import os
from datetime import date, datetime, time, timedelta
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

from typing import Optional, List, Dict

from mongoengine import Document, ListField, EmbeddedDocumentField, DictField, StringField, IntField, EmbeddedDocument
from pydantic import BaseModel, Field


# from scraper import PriceHistory


# class Todo(Base):
#     __tablename__ = "todos"
#
#     id = Column(Integer, primary_key=True)
#     title = Column(String(100))
#     complete = Column(Boolean, default=False)

class Criteria(EmbeddedDocument):
    manufacturer = DictField()
    model = StringField(max_length=50)
    year_start = IntField(max_length=50)
    year_end = IntField(max_length=50)
    hand_min = IntField(max_length=50)
    hand_max = IntField(max_length=50)
    km_min = IntField(max_length=50)
    km_max = IntField(max_length=50)
    price_min = IntField(max_length=50)
    price_max = IntField(max_length=50)


class Range(BaseModel):
    min: int
    max: int


class Task(BaseModel):
    id: str
    mail: str
    active: bool
    created_at: datetime
    last_run: datetime
    params: dict
    manufacturers: Optional[List[str]] = None
    car_models: Optional[List[str]] = None
    car_submodels: Optional[List[str]] = None
    # criteria: CarCriteria


def create_task_from_dict(task_dict: dict) -> Task:
    task_ = Task(**task_dict)
    return task_


class PriceHistory(BaseModel):
    price: int
    date: datetime


class AdDetails(BaseModel):
    # Fields without default values
    id: str
    car_model: str
    year: int
    price: float
    date_added_epoch: int
    date_added: datetime
    feed_source: str

    # Fields with default values
    full_info: Optional[Dict] = None
    city: str = 'N/A'
    manufacturer_he: str = 'N/A'
    hp: Optional[int] = None
    hand: Optional[int] = None
    kilometers: Optional[int] = None
    prices: List[PriceHistory] = Field(default=None)
    prices_handz: List[Dict] = Field(default=None)
    blind_spot: Optional[str] = None
    smart_cruise_control: Optional[str] = None
    manuf_en: str = 'N/A'
    gear_type: str = 'N/A'
    test_date: str = 'N/A'
    month_on_road: str = 'N/A'
