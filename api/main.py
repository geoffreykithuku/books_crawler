import os
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any # Added Dict, Any for BookListResponse
from db.client import db, ensure_indexes
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import asyncio
from datetime import datetime, timedelta, timezone
from crawler.models import Book # Import the Book model
from bson import ObjectId
from scheduler.reporter import generate_daily_change_report

load_dotenv()

API_KEY = os.getenv("API_KEY", "testkey123")
RATE_LIMIT_PER_HOUR = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))

app = FastAPI(title="Books API")

# Simple in-memory rate limiter: {api_key: [(timestamp1),(timestamp2),...]}
RATE_STORE = {}

async def require_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    # rate limiting
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=1)
    hits = RATE_STORE.get(x_api_key, [])
    # remove old hits
    hits = [t for t in hits if t > window_start]
    if len(hits) >= RATE_LIMIT_PER_HOUR:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    hits.append(now)
    RATE_STORE[x_api_key] = hits
    return x_api_key

@app.on_event("startup")
async def startup_event():
    await ensure_indexes()

# Define a Pydantic model for the paginated list response
class BookListResponse(BaseModel):
    page: int
    per_page: int
    data: List[Book]

@app.get("/books", response_model=BookListResponse, response_model_exclude={
    "data": {
        "__all__": {"raw_html_snapshot"}
    }
}, dependencies=[Depends(require_api_key)])
async def list_books(
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    rating: Optional[int] = None,
    sort_by: Optional[str] = "rating",
    page: int = 1,
    per_page: int = 20
):
    query = {}
    if category:
        query["category"] = category
    if rating:
        query["rating"] = rating
    if min_price is not None or max_price is not None:
        sub = {}
        if min_price is not None:
            sub["$gte"] = min_price
        if max_price is not None:
            sub["$lte"] = max_price
        query["price_including_tax"] = sub

    cursor = db.books.find(query)
    if sort_by == "price":
        cursor = cursor.sort("price_including_tax", 1)
    elif sort_by == "rating":
        cursor = cursor.sort("rating", -1)
    elif sort_by == "reviews":
        cursor = cursor.sort("num_reviews", -1)

    skip = (page - 1) * per_page
    docs = await cursor.skip(skip).limit(per_page).to_list(length=per_page)
    
    # Convert ObjectId to str for each document
    for doc in docs:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])

    return {"page": page, "per_page": per_page, "data": docs}

@app.get("/books/{book_id}", response_model=Book, response_model_exclude={"raw_html_snapshot"}, dependencies=[Depends(require_api_key)])
async def get_book(book_id: str):
    # book_id is assumed to be the Mongo _id as string OR source_url; we will check both
    from bson import ObjectId
    doc = None
    try:
        doc = await db.books.find_one({"_id": ObjectId(book_id)})
    except Exception:
        doc = await db.books.find_one({"source_url": book_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Convert ObjectId to str for the document
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    
    return doc

# Define a Pydantic model for the change records if they also contain ObjectIds
# For simplicity, assuming changes collection might also have _id, let's define a basic one.
class ChangeRecord(BaseModel):
    id: Optional[str] = Field(alias="_id")
    source_url: str
    changed_at: datetime
    old_fingerprint: Optional[str]
    new_fingerprint: Optional[str]
    old: Optional[Dict[str, Any]] # Store old and new as generic dicts for now
    new: Optional[Dict[str, Any]]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

@app.get("/changes", response_model=List[ChangeRecord], dependencies=[Depends(require_api_key)])
async def get_changes(limit: int = 50):
    docs = await db.changes.find().sort("changed_at", -1).limit(limit).to_list(length=limit)
    return docs

@app.get("/report/daily_changes", dependencies=[Depends(require_api_key)])
async def get_daily_change_report(format: str = Query("json", regex="^(json|csv)$")):
    if format == "json":
        report = await generate_daily_change_report(format="json")
        return JSONResponse(content=report)
    elif format == "csv":
        report = await generate_daily_change_report(format="csv")
        return JSONResponse(content=report, media_type="text/csv")
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Choose 'json' or 'csv'.")
