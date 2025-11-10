
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "bookscrape")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

async def ensure_indexes():
    # Book collection indexes
    await db.books.create_index("source_url", unique=True)
    await db.books.create_index("fingerprint")
    await db.changes.create_index([("changed_at", -1)])
    
    # Crawler state collection indexes
    await db.crawler_state.create_index("crawler_id", unique=True)
