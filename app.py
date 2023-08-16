import hashlib

import database
import json
from starlette.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
import pathlib
import models

BASE_DIR = pathlib.Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"

app = FastAPI()
templates = Jinja2Templates(directory=TEMPLATE_DIR)
app.mount("/static", StaticFiles(directory="static"), name="static")

car_ads = []

# Replace this with your actual data source or logic
models_data = {
    "hyundai": ["all", "Santa Fe", "Tucson"],
    "kia": ["all", "Sportage", 'Niro'],
    "seat": ["all", "Arona", "Ateca"],
    "mg": ["all", "ehs phev"]
}

manufacturers = [{"hyundai": "יונדאי"},
                 {"kia": "קיה"},
                 {"seat": "סיאט"}]


@app.on_event("startup")
def startup_event():
    database.init_db()


@app.get("/manufacturers")
async def get_manufacturers():
    with open("json/manufacturers.json", "r") as manufs:
        return json.load(manufs)


@app.get("/models/{manufacturer}")
async def get_models(manufacturer: str):
    if manufacturer in models_data:
        return {"models": models_data[manufacturer]}
    else:
        return {"models": []}


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


@app.get("/tasks")
async def root():
    tasks = models.Task.objects.all()
    return json.loads(tasks.to_json())
