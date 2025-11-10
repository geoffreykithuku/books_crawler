
from bs4 import BeautifulSoup
from typing import Optional, Dict
import re
from urllib.parse import urljoin

BASE = "https://books.toscrape.com/"

rating_map = {"One":1,"Two":2,"Three":3,"Four":4,"Five":5}

def _to_float(s: str) -> Optional[float]:
    if not s: return None
    m = re.search(r"([\d,.]+)", s)
    if not m: return None
    return float(m.group(1).replace(",", ""))

def parse_book_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.select_one("div.product_main h1")
    title = title_el.get_text(strip=True) if title_el else None

    desc_el = soup.select_one("#product_description ~ p")
    description = desc_el.get_text(strip=True) if desc_el else None

    # category from breadcrumb
    cat = None
    try:
        crumbs = soup.select("ul.breadcrumb li a")
        if crumbs and len(crumbs) >= 3:
            cat = crumbs[-1].get_text(strip=True)
    except Exception:
        cat = None

    # table values
    table = {}
    for tr in soup.select("table.table.table-striped tr"):
        key = tr.th.get_text(strip=True)
        val = tr.td.get_text(strip=True)
        table[key] = val

    p_inc = _to_float(table.get("Price (incl. tax)", ""))
    p_exc = _to_float(table.get("Price (excl. tax)", ""))
    availability = table.get("Availability") or (soup.select_one("p.availability").get_text(strip=True) if soup.select_one("p.availability") else None)
    num_reviews = int(table.get("Number of reviews", "0") or 0)

    # image url
    img_el = soup.select_one("div.carousel img") or soup.select_one("div.item.active img") or soup.select_one("img")
    image_url = None
    if img_el and img_el.get("src"):
        src = img_el["src"]
        image_url = urljoin(BASE, src) if src.startswith("../") or src.startswith("./") else urljoin(url, src)

    rating = None
    rating_el = soup.select_one("p.star-rating")
    if rating_el:
        for c in rating_el.get("class", []):
            if c in rating_map:
                rating = rating_map[c]

    return {
        "source_url": url,
        "title": title,
        "description": description,
        "category": cat,
        "price_including_tax": p_inc,
        "price_excluding_tax": p_exc,
        "availability": availability,
        "num_reviews": num_reviews,
        "image_url": image_url,
        "rating": rating,
    }
