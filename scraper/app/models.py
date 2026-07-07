from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class ExtractMenuRequest(BaseModel):
    url: str
    restaurant_name: Optional[str] = None


class MenuItem(BaseModel):
    id: str
    restaurant_url: str
    restaurant_name: str = ""
    item: str
    item_type: str = "food"
    cuisine: str = "unknown"
    price: Optional[float] = None
    currency: str = ""
    section: str = ""
    description: str = ""
    source_url: str = ""
    scraped_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExtractMenuResponse(BaseModel):
    status: str
    restaurant_url: str
    source_urls: List[str]
    parser_used: str
    items_count: int
    items: List[MenuItem]
