from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel


class PriceHistory(BaseModel):
    price: int
    date: datetime


class CarDetails(BaseModel):
    # Fields without default values
    id: str
    car_model: str
    year: int
    price: float
    date_added_epoch: int
    date_added: str
    feed_source: str

    # Fields with default values
    city: str = 'N/A'
    manufacturer_he: str = 'N/A'
    hp: Optional[int] = None
    hand: Optional[int] = None
    kilometers: Optional[int] = None
    prices: List[PriceHistory] = field(default_factory=list)
    blind_spot: Optional[str] = None
    smart_cruise_control: Optional[str] = None
    manuf_en: str = 'N/A'
    updated_at: Optional[str] = None
    gear_type: str = 'N/A'
