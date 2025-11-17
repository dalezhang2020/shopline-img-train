"""
Data models and response schemas
"""
from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel


class SyncResponse(BaseModel):
    """Response model for sync operations"""
    success: bool
    message: str
    records_synced: int
    execution_time: float
    table_name: str
    sync_mode: str
    error: Optional[str] = None


class ProductVariant(BaseModel):
    """Product variant data model"""
    product_id: str
    listing_id: str
    website_name: str
    is_visible: str
    date_created: str
    sku: str
    price: Optional[float] = None
    sale_price: Optional[float] = None
    inventory_level: int
    image_url: str
    custom_url: str
    handle: str
    inventory_item_id: str
    productimg_url: str
    variant_id: str


class HistoryRecord(BaseModel):
    """History record data model"""
    listing_id: str
    sku: str
    price: Optional[float] = None
    sale_price: Optional[float] = None
    inventory_level: int
    is_visible: str
    recorddate: str
