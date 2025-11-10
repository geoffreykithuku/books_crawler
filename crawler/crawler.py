
import asyncio
import hashlib
import os
from datetime import datetime, timezone
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .parser import parse_book_page
from db.client import db
from dotenv import load_dotenv
from utils.logger import logger

load_dotenv()
BASE = "https://books.toscrape.com/"
CONCURRENCY = int(os.getenv("CRAWL_CONCURRENCY", "8"))

def fingerprint(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

@retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(5),
       retry=retry_if_exception_type(httpx.RequestError))
async def fetch(client: httpx.AsyncClient, url: str) -> str:
    r = await client.get(url, timeout=20.0)
    r.raise_for_status()
    return r.text

async def store_book(doc: dict):
    # upsert by source_url
    doc["crawl_timestamp"] = datetime.now(timezone.utc)
    result = await db.books.update_one(
        {"source_url": doc["source_url"]},
        {"$set": doc, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True
    )
    
    # Check if this was a new book (upserted)
    if result.upserted_id:
        msg = f"New book discovered:\n"
        msg += f"Title: {doc.get('title', 'Unknown Title')}\n"
        msg += f"Category: {doc.get('category', 'Unknown Category')}\n"
        msg += f"Price: £{doc.get('price_including_tax', 0.0):.2f}\n"
        msg += f"URL: {doc['source_url']}"
        logger.alert("New Book Added", msg, level="info")

async def fetch_book_and_store(client: httpx.AsyncClient, book_url: str, sem: asyncio.Semaphore):
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        async with sem:
            try:
                html = await fetch(client, book_url)
                parsed = parse_book_page(html, book_url)
                fp = fingerprint(html)
                parsed["fingerprint"] = fp
                parsed["raw_html_snapshot"] = html
                
                # check existing fingerprint
                existing = await db.books.find_one({"source_url": book_url}, {"fingerprint": 1})
                if existing and existing.get("fingerprint") == fp:
                    # update crawl timestamp only
                    await db.books.update_one({"source_url": book_url}, {"$set": {"crawl_timestamp": datetime.now(timezone.utc)}})
                    return
                
                await store_book(parsed)
                return  # Success, exit the retry loop
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning("Failed to process book: %s, attempt %d of %d. Error: %s", 
                                 book_url, attempt + 1, max_retries, str(e))
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error("Failed to process book after %d attempts: %s, %s", 
                               max_retries, book_url, str(e))
                    raise  # Re-raise the last exception after all retries are exhausted

async def get_crawler_state():
    """Retrieve the last known state of the crawler"""
    state = await db.crawler_state.find_one({"crawler_id": "main"})
    return state

async def save_crawler_state(next_url: str, completed_urls: list):
    """Save the current state of the crawler"""
    await db.crawler_state.update_one(
        {"crawler_id": "main"},
        {
            "$set": {
                "last_page_url": next_url,
                "completed_urls": completed_urls,
                "updated_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )

async def crawl_all():
    async with httpx.AsyncClient() as client:
        sem = asyncio.Semaphore(CONCURRENCY)
        completed_urls = []

        # Try to resume from last state
        state = await get_crawler_state()
        next_url = state.get("last_page_url") if state else BASE
        if state and state.get("completed_urls"):
            completed_urls = state["completed_urls"]
            logger.info("Resuming crawl from page: %s", next_url)
        else:
            next_url = BASE
            logger.info("Starting new crawl from beginning")

        tasks = []
        try:
            while next_url:
                logger.info("Fetching page: %s", next_url)
                page_html = await fetch(client, next_url)
                soup = BeautifulSoup(page_html, "lxml")
                
                # extract all book links from page
                for a in soup.select("article.product_pod h3 a"):
                    rel = a["href"]
                    book_url = urljoin(next_url, rel)
                    if book_url not in completed_urls:  # Skip already processed books
                        tasks.append(fetch_book_and_store(client, book_url, sem))
                        completed_urls.append(book_url)
                
                # Save state after processing each page
                await save_crawler_state(next_url, completed_urls)
                
                # find next page link
                next_link = soup.select_one("li.next a")
                if next_link:
                    next_url = urljoin(next_url, next_link["href"])
                else:
                    next_url = None
            
            # Wait for all book processing tasks to complete
            await asyncio.gather(*tasks)
            
            # Clear the state after successful completion
            await save_crawler_state(None, [])
            logger.info("Crawl completed successfully")
            
        except Exception as e:
            logger.error("Crawl interrupted: %s", str(e))
            # State is already saved, so we can resume from here next time
            raise

if __name__ == "__main__":
    asyncio.run(crawl_all())
