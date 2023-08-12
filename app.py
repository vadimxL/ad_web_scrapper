import hashlib

import database
import json
from starlette import status
from starlette.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from fastapi import Request, HTTPException, FastAPI, Form, Depends
from fastapi.templating import Jinja2Templates
import pathlib

from starlette.responses import HTMLResponse

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


def get_manufacturers():
    with open("json/manufacturers.json", "r") as manufs:
        return json.load(manufs)

@app.on_event("startup")
def startup_event():
    database.init_db()

@app.get("/models/{manufacturer}")
async def get_models(manufacturer: str):
    if manufacturer in models_data:
        return {"models": models_data[manufacturer]}
    else:
        raise HTTPException(status_code=404, detail="Manufacturer not found")


@app.post("/add")
def add(req: Request, select_manufacturer: str = Form(...)
        , select_start_year: int = Form(...), select_end_year: int = Form(...)):
    attributes_string = f"{select_manufacturer}{select_start_year}{select_end_year}"
    criteria = models.Criteria(manufacturer=select_manufacturer, year_range=f"{select_start_year}-{select_end_year}")
    new_task = models.Task(id=hashlib.md5(attributes_string.encode()).hexdigest(), criteria=criteria)
    new_task.save()
    url = app.url_path_for("root")
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    start_year = 2010
    end_year = 2024
    years = list(range(start_year, end_year + 1))
    tasks = models.Task.objects.all()
    context = {
        "tasks_list": tasks,
        "request": request,
        "car_ads": car_ads,
        "years": years,
        "manuf_list": get_manufacturers(),
    }
    return templates.TemplateResponse("index.html", context=context)
