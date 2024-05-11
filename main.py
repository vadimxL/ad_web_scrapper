import asyncio
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from typing import List
from urllib import parse
from pydantic import BaseModel, EmailStr
from starlette.middleware.cors import CORSMiddleware
import firebase_db
import json
from fastapi import FastAPI, HTTPException

from db_handler import DbHandler
from scraper import Scraper, urls, logger, manufacturers_dict, num_to_manuf_dict, num_to_model_dict
import models

app = FastAPI()

# Allow all origins with appropriate methods, headers, and credentials if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],  # You can specify specific methods (e.g., ["GET", "POST"])
    allow_headers=["*"],  # You can specify specific headers if needed
)

urls_to_scrape = ["https://www.yad2.co.il/vehicles/cars?manufacturer=48&model=3866,2829,3484&year=2019--1&km=-1-80000"]

# Replace this with your actual data source or logic
manufacturers = {}
manufacturers_list = []
car_models = {}


@app.on_event("startup")
def startup_event():
    global manufacturers_list
    try:
        firebase_db.init_firebase_db()
    except Exception as e:
        logger.error(f"Error initializing firebase db: {e}")
    scraper = Scraper()
    search_opts = scraper.get_search_options()
    manufacturers_list = search_opts['data']['manufacturer']
    for manuf in search_opts['data']['manufacturer']:
        manufacturers[manuf['value']] = manuf['text']
    with open("manufacturers.json", "w") as manufs:
        json.dump(manufacturers, manufs)
    # print(manufacturers)


@app.get("/manufacturers")
async def get_manufacturers():
    logging.info(f"Getting manufacturer list")
    return manufacturers_list


def extract_query_params(url: str) -> dict:
    # Extract query parameters from the URL
    params = dict(parse.parse_qsl(parse.urlsplit(url).query))
    return params


tasks = dict()


@app.get("/tasks", response_model=List[models.Task])
async def read_items():
    logger.info(f"Getting tasks: {tasks}")
    return list(tasks.values())


async def scrape_task(task_id: str, minutes=5.0):
    params = extract_query_params(tasks[task_id].title)
    logger.info(f"Scraping task: {task_id}: {tasks[task_id]}")
    scraper = Scraper()
    task = asyncio.get_event_loop().create_task(scraper.run(params))
    results = await task
    db_handler = DbHandler(parse.urlsplit(tasks[task_id].title).query)
    db_handler.create_collection(results)
    while True:
        logger.info(f"Sleeping for {timedelta(minutes=minutes).seconds} seconds")
        await asyncio.sleep(timedelta(minutes=minutes).seconds)
        # Scrapping again
        task = asyncio.get_event_loop().create_task(scraper.run(params))
        results = await task
        db_handler.handle_results(results)

@app.post("/tasks", response_model=models.Task)
async def create_item(email: EmailStr, url: str):
    params: dict = extract_query_params(url)

    if 'manufacturer' not in params or 'model' not in params or 'year' not in params or 'km' not in params:
        raise HTTPException(status_code=400, detail="Invalid URL")

    criteria = models.CarCriteria(manufacturer=params['manufacturer'],
                                  models=params['model'].split(','),
                                  year=get_range(params['year']),
                                  km=get_range(params['km']))
    id_ = hashlib.sha256(url.encode()).hexdigest()
    if id_ in tasks:
        return tasks[id_]
    task = models.Task(id=id_, title=url, mail=email,
                       created_at=datetime.now().strftime("%d_%m_%Y_%H_%M_%S"),
                       criteria=criteria)
    logger.info(f"Creating item {task}")
    tasks[id_] = task
    t = asyncio.get_event_loop().create_task(scrape_task(id_))
    return task


@app.put("/tasks/{task_id}", response_model=models.Task)
async def update_item(task_id: str, criteria: models.CarCriteria):
    task = tasks[task_id]
    task.criteria = criteria
    return task


@app.delete("/tasks/{task_id}")
async def delete_item(task_id: str):
    task = tasks.pop(task_id, None)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": f"Task: {task} deleted"}


def get_range(data: str) -> models.Range:
    # Split the data on the separator
    parts = data.split('-')
    parts = [int(part) for part in parts if part.isdigit()]
    parts = [part * -1 if part == 1 else part for part in parts]
    return models.Range(min=parts[0], max=parts[1])
