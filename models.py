from datetime import date, datetime, time, timedelta

from typing import Optional, List

from mongoengine import Document, ListField, EmbeddedDocumentField, DictField, StringField, IntField, EmbeddedDocument
from pydantic import BaseModel


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
    title: str
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


class PriceHistory(EmbeddedDocument):
    price = IntField()
    date = StringField(max_length=50)  # You might want to use a DateTimeField for date/time fields


class CarAd(Document):
    id = StringField(primary_key=True)
    manufacturer = StringField(max_length=50)
    model = StringField(max_length=50)
    year = IntField()
    hand = StringField(max_length=50)
    engine_size = IntField()
    kilometers = StringField(max_length=50)
    price = StringField(max_length=50)
    updated_at = StringField(max_length=50)
    date_added = StringField(max_length=50)
    price_history = ListField(EmbeddedDocumentField(PriceHistory))
