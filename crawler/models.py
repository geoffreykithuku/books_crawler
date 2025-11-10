from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId

class Book(BaseModel):
    id: Optional[str] = Field(alias="_id") # Add this line to handle MongoDB's _id
    source_url: HttpUrl
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    price_including_tax: Optional[float] = None
    price_excluding_tax: Optional[float] = None
    availability: Optional[str] = None
    num_reviews: Optional[int] = 0
    image_url: Optional[HttpUrl] = None
    rating: Optional[int] = None
    crawl_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "fetched"
    fingerprint: Optional[str] = None
    raw_html_snapshot: Optional[str] = None


    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }
