from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
import os
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

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
    full_info: Optional[Dict] = None
    city: str = 'N/A'
    manufacturer_he: str = 'N/A'
    hp: Optional[int] = None
    hand: Optional[int] = None
    kilometers: Optional[int] = None
    prices: List[PriceHistory] = Field(default=list)
    # prices_handz: List[Dict] = field(default_factory=list)
    prices_handz: str = 'N/A'
    blind_spot: Optional[str] = None
    smart_cruise_control: Optional[str] = None
    manuf_en: str = 'N/A'
    updated_at: Optional[str] = None
    gear_type: str = 'N/A'
    test_date: str = 'N/A'
    month_on_road: str = 'N/A'
