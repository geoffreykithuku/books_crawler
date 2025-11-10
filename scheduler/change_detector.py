
import asyncio
import hashlib
from datetime import datetime, timezone
from db.client import db
from utils.logger import logger, AlertLogger

alert_logger = AlertLogger("ChangeDetector")

def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

async def detect_changes_for_all_books():
    # For each book in DB, re-fetch the page and compare fingerprints
    from crawler.crawler import fetch, BASE  # reuse fetch and BASE
    import httpx
    async with httpx.AsyncClient() as client:
        cursor = db.books.find({}, {"source_url": 1, "fingerprint": 1})
        async for doc in cursor:
            url = doc["source_url"]
            old_fp = doc.get("fingerprint")
            try:
                html = await fetch(client, url)
            except Exception as e:
                alert_logger.error("Failed to fetch for change detection %s, %s", url, e)
                continue
            new_fp = fingerprint(html)
            if new_fp != old_fp:
                # parse new data
                from crawler.parser import parse_book_page
                parsed = parse_book_page(html, url)
                parsed["fingerprint"] = new_fp
                parsed["raw_html_snapshot"] = html
                parsed["crawl_timestamp"] = datetime.now(timezone.utc)
                # update main doc and write change record
                old_doc = await db.books.find_one({"source_url": url})
                await db.books.update_one({"source_url": url}, {"$set": parsed})
                # Record change and analyze significance
                old_price = old_doc.get("price_including_tax", 0)
                new_price = parsed.get("price_including_tax", 0)
                price_change_pct = ((new_price - old_price) / old_price * 100) if old_price else 0
                
                old_availability = old_doc.get("availability", "")
                new_availability = parsed.get("availability", "")
                
                # Record the change
                change = {
                    "source_url": url,
                    "changed_at": datetime.now(timezone.utc),
                    "old_fingerprint": old_fp,
                    "new_fingerprint": new_fp,
                    "old": old_doc,
                    "new": parsed,
                    "changes": []
                }
                
                # Track specific changes
                if old_price != new_price:
                    change["changes"].append("price")
                if old_availability != new_availability:
                    change["changes"].append("availability")
                
                await db.changes.insert_one(change)
                
                # Log and alert based on significance
                msg = f"Change detected for book: {parsed.get('title', 'Unknown Title')} ({url})\n"
                alert_needed = False
                
                if abs(price_change_pct) >= 10:  # Price changed by 10% or more
                    price_msg = f"Price changed significantly: £{old_price:.2f} → £{new_price:.2f} ({price_change_pct:+.1f}%)"
                    msg += price_msg + "\n"
                    alert_needed = True
                
                if old_availability != new_availability:
                    availability_msg = f"Availability changed: {old_availability} → {new_availability}"
                    msg += availability_msg + "\n"
                    if "In stock" not in old_availability and "In stock" in new_availability:
                        alert_needed = True  # Alert when book becomes available
                
                if alert_needed:
                    alert_logger.alert("Significant Book Changes Detected", msg, level="info")
                else:
                    alert_logger.info("Minor change detected: %s", url)
