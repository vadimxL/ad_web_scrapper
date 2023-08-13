import datetime

from mongoengine import Document, StringField, IntField, ListField, EmbeddedDocumentField, BooleanField, EmailField, \
    DateTimeField, DictField
from mongoengine import StringField, IntField, EmbeddedDocument


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
    year_range = StringField(max_length=50)
    hand_range = StringField(max_length=50)
    km_range = StringField(max_length=50)
    price_range = StringField(max_length=50)


class Task(Document):
    id = StringField(primary_key=True)
    # title = StringField(max_length=100)
    manufacturer = StringField(max_length=50)

    mail = EmailField(max_length=100)
    # complete = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    criteria = EmbeddedDocumentField(Criteria)


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
