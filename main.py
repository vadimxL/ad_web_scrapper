from starlette import status
from starlette.staticfiles import StaticFiles

import json
from contextlib import asynccontextmanager
from starlette.responses import RedirectResponse
from fastapi import Request, HTTPException, FastAPI, Form
from fastapi.templating import Jinja2Templates
import pathlib

from mongoengine import connect
from requests_cache import CachedSession
from starlette.responses import HTMLResponse

from scraper import KIA_MANUFACTURER_NUM, main, HYUNDAI_MANUFACTURER_NUM

BASE_DIR = pathlib.Path(__file__).resolve().parent
print(BASE_DIR)
TEMPLATE_DIR = BASE_DIR / "templates"
print(TEMPLATE_DIR)

app = FastAPI()
templates = Jinja2Templates(directory=TEMPLATE_DIR)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.post("/add")
def add(req: Request, title: str = Form(...)):
    # new_todo = models.Todo(title=title)
    # db.add(new_todo)
    # db.commit()
    print(title)
    url = app.url_path_for("root")
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/vehicleCriteria")
async def vehicle_criteria():
    pass


# Replace this with your actual data source or logic
models_data = {
    "Hyundai": ["Niro", "Santa Fe", "Tucson"],
    "Kia": ["Optima", "Soul", "Sportage"]
}

manufacturers = ["Hyundai", "Kia"]


@app.get("/manufacturers")
async def get_manufacturers():
    return manufacturers


@app.get("/api/models")
async def get_models(manufacturer: str):
    if manufacturer in models_data:
        return {"models": models_data[manufacturer]}
    else:
        raise HTTPException(status_code=404, detail="Manufacturer not found")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    try:
        # Connect to the MongoDB database
        connections = connect(
            db="favorites_yad2",
            host="localhost",
            port=27018,
            username="root",
            password="example",
            authentication_source="admin"
        )
        print(f"Connected to MongoDB: {connections}")
    except Exception as e:
        print(f"Connection failed: {e}")
        exit()

    hyundai_querystring = {"year": "2020--1", "price": "80000-135000", "km": "500-40000", "hand": "-1-2",
                           "priceOnly": "1",
                           "imgOnly": "1", "page": "1", "manufacturer": str(HYUNDAI_MANUFACTURER_NUM),
                           "carFamilyType": "10,5", "forceLdLoad": "true"}

    kia_querystring = {"year": "2020--1", "priceOnly": "1", "model": "2829,3484,3223,3866",
                       "imgOnly": "1", "page": "1", "manufacturer": str(KIA_MANUFACTURER_NUM),
                       "carFamilyType": "10,5", "forceLdLoad": "true"}

    context = {
        "request": request,
        "car_ads": json.load(open("json/car_ads.json", "r")),
    }
    return templates.TemplateResponse("index.html", context=context)


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
