import hashlib
import logging
from typing import Union, List, Annotated
from urllib import parse

from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

import firebase_db
import json
from starlette.staticfiles import StaticFiles
from fastapi import FastAPI, Query
from fastapi.templating import Jinja2Templates
import pathlib
import models
import scraper

BASE_DIR = pathlib.Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"

app = FastAPI()

# Allow all origins with appropriate methods, headers, and credentials if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],  # You can specify specific methods (e.g., ["GET", "POST"])
    allow_headers=["*"],  # You can specify specific headers if needed
)

templates = Jinja2Templates(directory=TEMPLATE_DIR)
app.mount("/static", StaticFiles(directory="static"), name="static")

url_to_scrape = "https://www.yad2.co.il/vehicles/cars?manufacturer=48&model=3866,2829,3484&year=2019--1&km=-1-80000"

# Replace this with your actual data source or logic
manufacturers = {}
manufacturers_list = []
car_models = {}


@app.on_event("startup")
def startup_event():
    global manufacturers_list
    firebase_db.init_firebase_db()
    search_opts = scraper.get_search_options()
    manufacturers_list = search_opts['data']['manufacturer']
    for manuf in search_opts['data']['manufacturer']:
        manufacturers[manuf['value']] = manuf['text']
    # print(manufacturers)


@app.get("/manufacturers")
async def get_manufacturers():
    logging.info(f"Getting manufacturer list")
    return manufacturers_list


@app.get("/models/{manufacturer}")
async def get_models(manufacturer: str):
    logging.info(manufacturer)
    res = scraper.get_model(manufacturer)['data']['model']
    logging.info(res)
    return res


# @app.get("/models/{manufacturer}")
# async def get_models(manufacturer: str):
#     if manufacturer in models_data:
#         return {"models": models_data[manufacturer]}
#     else:
#         return {"models": []}


@app.get("/ads")
async def get_ads():
    q = {
        'manufacturer': '48',
        'model': '3866,2829,3484',
        'year': '2019--1',
        'km': '-1-80000'
    }
    car_ads = scraper.main(q)
    return {"ads": car_ads}


@app.post("/add/")
def add(manufacturer_val: int, start_year: int, end_year: int):
    manuf = {}
    with open("json/manufacturers.json", "r") as manufs:
        for m in json.load(manufs):
            if m["value"] == manufacturer_val:
                manuf = m
                break
    attributes_string = f"{manufacturer_val}{start_year}{end_year}"
    criteria = models.Criteria(manufacturer=manuf, year_start=start_year, year_end=end_year)
    new_task = models.Task(id=hashlib.md5(attributes_string.encode()).hexdigest(), criteria=criteria)
    new_task.save()
    return "Successfully added to DB"


class CarData(BaseModel):
    manufacturer: int
    model: str
    year: str
    km: str


def extract_query_params(url: str) -> dict:
    # Extract query parameters from the URL
    params = dict(parse.parse_qsl(parse.urlsplit(url).query))
    return params


@app.get("/scrape/cars/")
async def read_items(manufacturer: str = '48', model: str | None = None, year: str | None = None,
                     km: str | None = None):
    print(manufacturer, model, year, km)
    if model is not None:
        model = scraper.get_model(manufacturer)

    return {"manufacturer": manufacturers[manufacturer], "model": model, "year": year, "km": km}


# url_to_scrape = "https://www.yad2.co.il/vehicles/cars?manufacturer=48&model=3866,2829,3484&year=2019--1&km=-1-80000"

class Range(BaseModel):
    min: int
    max: int


class Item(BaseModel):
    id: int
    email: str
    manufacturers: list
    models: list
    year_range: Range
    mileage_range: Range
    price_range: Range


items = []


@app.get("/items", response_model=List[Item])
async def read_items():
    logging.info(f"Getting items: {items}")
    return items


@app.post("/items", response_model=Item)
async def create_item(item: Item):
    logging.info(f"Creating item {item}")
    items.append(item)
    return item


@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: Item):
    items[item_id] = item
    return item


@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    del items[item_id]
    return {"message": "Item deleted"}
