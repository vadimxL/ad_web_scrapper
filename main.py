import asyncio
import dataclasses
import hashlib
import logging
from dataclasses import dataclass

from datetime import datetime, timedelta
from typing import List, Dict
from urllib import parse
from pydantic import BaseModel, EmailStr
from starlette.middleware.cors import CORSMiddleware
import firebase_db
import json
from fastapi import FastAPI, HTTPException

from car_details import CarDetails
from db_handler import DbHandler
from gmail_sender.gmail_sender import GmailSender
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
gmail_sender = GmailSender(credentials_path="gmail_sender/credentials.json")


@app.on_event("startup")
def startup_event():
    global manufacturers_list
    try:
        firebase_db.init_firebase_db()
    except Exception as e:
        logger.error(f"Error initializing firebase db: {e}")
    scraper = Scraper(cache_timeout_min=5)
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


@dataclass
class InternalTask:
    task: asyncio.Task
    task_info: models.Task


tasks: Dict[str, InternalTask] = dict()


@app.get("/tasks", response_model=List[models.Task])
async def read_items():
    return [task.task_info for task in tasks.values()]


async def scrape_task(task_id: str):
    params = extract_query_params(tasks[task_id].task_info.title)
    logger.info(f"Scraping task: {task_id}: {tasks[task_id]}")
    scraper = Scraper(cache_timeout_min=30)
    task = asyncio.get_event_loop().create_task(scraper.run(params))
    results: List[CarDetails] = await task
    time_now = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    filename_json = f'json/car_ads_{task_id}' + time_now + '.json'
    with open(filename_json, 'w', encoding='utf-8') as f1:
        json.dump({ad.id: ad.model_dump(mode='json') for ad in results}, f1, indent=4, ensure_ascii=False)
    db_handler = DbHandler(parse.urlsplit(tasks[task_id].task_info.title).query, gmail_sender)
    db_handler.create_collection(results)
    while True:
        # Scrapping again
        minutes = tasks[task_id].task_info.duration
        task = asyncio.get_event_loop().create_task(scraper.run(params))
        results = await task
        db_handler.handle_results(results)
        logger.info(f"Sleeping for {timedelta(minutes=minutes).seconds} seconds")
        await asyncio.sleep(timedelta(minutes=minutes).seconds)


@app.post("/tasks", response_model=models.Task)
async def create_item(email: EmailStr, duration: int, url: str):
    params: dict = extract_query_params(url)

    if 'manufacturer' not in params or 'model' not in params or 'year' not in params or 'km' not in params:
        raise HTTPException(status_code=400, detail="Invalid URL")

    id_ = hashlib.sha256(url.encode()).hexdigest()
    if id_ in tasks:
        return tasks[id_].task_info
    task_info = models.Task(id=id_, title=url, mail=email,
                       created_at=datetime.now().strftime("%d_%m_%Y_%H_%M_%S"),
                       duration=duration)
    logger.info(f"Creating item {task_info}")
    t: asyncio.Task = asyncio.get_event_loop().create_task(scrape_task(id_))
    tasks[id_] = InternalTask(task=t, task_info=task_info)
    return task_info


@app.put("/tasks/{task_id}")
async def update_item(task_id: str, duration: int):
    if task_id not in tasks:
        return {"message": f"Task: {task_id} not found"}
    task = tasks[task_id]
    task.task_info.duration = duration
    logger.info(f"Updating item {task.task_info} with duration {duration}")
    return task.task_info


@app.delete("/tasks/{task_id}")
async def delete_item(task_id: str):
    if task_id not in tasks:
        return {"message": f"Task: {task_id} not found"}
    task: InternalTask = tasks.pop(task_id)
    task.task.cancel()
    return {"message": f"Task: {task.task_info} deleted"}


def get_range(data: str) -> models.Range:
    # Split the data on the separator
    parts = data.split('-')
    parts = [int(part) for part in parts if part.isdigit()]
    parts = [part * -1 if part == 1 else part for part in parts]
    return models.Range(min=parts[0], max=parts[1])
