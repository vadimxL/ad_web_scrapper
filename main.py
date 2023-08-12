import json

from starlette import status
from starlette.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from fastapi import Request, HTTPException, FastAPI, Form
from fastapi.templating import Jinja2Templates
import pathlib
from mongoengine import connect
from starlette.responses import HTMLResponse
from scraper import manufacturers_dict, yad2_scrape

BASE_DIR = pathlib.Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"

app = FastAPI()
templates = Jinja2Templates(directory=TEMPLATE_DIR)
app.mount("/static", StaticFiles(directory="static"), name="static")

car_ads = []



@app.post("/add")
def add(select_manufacturer: str = Form(...), start_year: int = Form(...), end_year: int = Form(...)):
    global car_ads
    query = {"year": f"{start_year}-{end_year}", "price": "80000-135000", "km": "500-40000", "hand": "-1-2",
             "priceOnly": "1", "imgOnly": "1", "page": "1", "manufacturer": select_manufacturer,
             "forceLdLoad": "true"}
    car_ads = yad2_scrape(query)
    url = app.url_path_for("root")
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/vehicleCriteria")
async def vehicle_criteria():
    pass


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


@app.get("/models/{manufacturer}")
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

    start_year = 2010
    end_year = 2024
    years = list(range(start_year, end_year + 1))

    context = {
        "request": request,
        "car_ads": car_ads,
        "years": years,
        "manuf_list": get_manufacturers(),
    }
    return templates.TemplateResponse("index.html", context=context)
