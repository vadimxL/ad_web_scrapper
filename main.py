import asyncio
import hashlib
import logging
import threading
import time
from dataclasses import dataclass
import schedule

from datetime import datetime, timedelta
from typing import List, Dict
from urllib import parse
from pydantic import EmailStr
from starlette.middleware.cors import CORSMiddleware
import firebase_db
import json
from fastapi import FastAPI, HTTPException

from car_details import CarDetails
from db_handler import DbHandler
from gmail_sender.gmail_sender import GmailSender
from scraper import Scraper, logger
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
    # scraper = Scraper(cache_timeout_min=5)
    search_opts = Scraper.get_search_options()
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


@app.get("/models/{manufacturer_id}")
async def get_models(manufacturer_id: str):
    logging.info(f"Getting models for manufacturer: {manufacturer_id}")
    # scraper = Scraper(cache_timeout_min=5)
    models = await Scraper.get_model(manufacturer_id)
    print(models)
    return models['data']['model']


def extract_query_params(url: str) -> dict:
    # Extract query parameters from the URL
    params = dict(parse.parse_qsl(parse.urlsplit(url).query))
    return params


@dataclass
class InternalTask:
    event: threading.Event
    task_info: models.Task


tasks: Dict[str, InternalTask] = dict()


@app.get("/tasks", response_model=List[models.Task])
async def read_items():
    return [task.task_info for task in tasks.values()]


def run_continuously(interval=1):
    """Continuously run, while executing pending jobs at each
    elapsed time interval.
    @return cease_continuous_run: threading. Event which can
    be set to cease continuous run. Please note that it is
    *intended behavior that run_continuously() does not run
    missed jobs*. For example, if you've registered a job that
    should run every minute and you set a continuous run
    interval of one hour then your job won't be run 60 times
    at each interval but only once.
    """
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run


def recurrent_scrape(task_id: str, params: dict, loop):
    scraper = Scraper(cache_timeout_min=30)
    db_handler = DbHandler(parse.urlsplit(tasks[task_id].task_info.title).query, gmail_sender)
    results = scraper.run(params, loop)
    logger.info(f"Recurrence task: {task_id}: {tasks[task_id]}")
    db_handler.handle_results(results)


def scrape_task(task_id: str, loop):
    params = extract_query_params(tasks[task_id].task_info.title)
    logger.info(f"Scraping task: {task_id}: {tasks[task_id]}")
    scraper = Scraper(cache_timeout_min=30)
    results: List[CarDetails] = scraper.run(params, loop)
    time_now = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    filename_json = f'json/car_ads_{task_id}' + time_now + '.json'
    with open(filename_json, 'w', encoding='utf-8') as f1:
        json.dump({ad.id: ad.model_dump(mode='json') for ad in results}, f1, indent=4, ensure_ascii=False)
    db_handler = DbHandler(parse.urlsplit(tasks[task_id].task_info.title).query, gmail_sender)
    db_handler.create_collection(results)
    # Do some work that only needs to happen once...
    return schedule.CancelJob


@app.post("/tasks", response_model=models.Task)
async def create_item(email: EmailStr, url: str):
    params: dict = extract_query_params(url)

    if 'manufacturer' not in params or 'model' not in params or 'year' not in params or 'km' not in params:
        raise HTTPException(status_code=400, detail="Invalid URL")

    id_ = hashlib.sha256(url.encode()).hexdigest()
    if id_ in tasks:
        return tasks[id_].task_info
    task_info = models.Task(id=id_, title=url, mail=email,
                            created_at=datetime.now().strftime("%d_%m_%Y_%H_%M_%S"))
    loop = asyncio.get_event_loop()
    schedule.every(1).seconds.do(scrape_task, id_, loop)
    schedule.every(6).hours.do(recurrent_scrape, id_, params, loop)
    event_ = run_continuously()
    tasks[id_] = InternalTask(event=event_, task_info=task_info)
    # Start the background thread
    return task_info


# @app.put("/tasks/{task_id}")
# async def update_item(task_id: str, duration: int):
#     if task_id not in tasks:
#         return {"message": f"Task: {task_id} not found"}
#     task = tasks[task_id]
#     task.task_info.duration = duration
#     logger.info(f"Updating item {task.task_info} with duration {duration}")
#     return task.task_info


@app.delete("/tasks/{task_id}")
async def delete_item(task_id: str):
    if task_id not in tasks:
        return {"message": f"Task: {task_id} not found"}
    task: InternalTask = tasks.pop(task_id)
    # Stop the background thread
    task.event.set()
    return {"message": f"Task: {task.task_info} deleted"}


def get_range(data: str) -> models.Range:
    # Split the data on the separator
    parts = data.split('-')
    parts = [int(part) for part in parts if part.isdigit()]
    parts = [part * -1 if part == 1 else part for part in parts]
    return models.Range(min=parts[0], max=parts[1])
