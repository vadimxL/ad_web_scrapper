import asyncio
import hashlib
import logging
import os
import threading
import time
from io import BytesIO
import pandas as pd
import schedule
from datetime import datetime, timedelta
from typing import List, Dict
from urllib import parse
from pydantic import EmailStr
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

import db_handler
import firebase_db
import json
from fastapi import FastAPI, HTTPException
from car_details import CarDetails
from db_handler import DbHandler
from email_sender.email_sender import EmailSender
from persistence import dump_to_excel_car_details
import models
from logger_setup import internal_info_logger
from scraper import Scraper

app = FastAPI()

# Allow all origins with appropriate methods, headers, and credentials if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],  # You can specify specific methods (e.g., ["GET", "POST"])
    allow_headers=["*"],  # You can specify specific headers if needed
    expose_headers=["*"]
)

# Replace this with your actual data source or logic
manufacturers = {}
manufs_unaltered = []


# gmail_sender = GmailSender(credentials_path="gmail_sender/credentials.json", token_path="gmail_sender/token.json")


@app.on_event("startup")
def startup_event():
    global manufs_unaltered
    try:
        firebase_db.init_firebase_db()
    except Exception as e:
        internal_info_logger.error(f"Error initializing firebase db: {e}")
    # scraper = Scraper(cache_timeout_min=5)
    search_opts = Scraper.get_search_options()
    manufs_unaltered = search_opts['data']['manufacturer']
    for manuf in search_opts['data']['manufacturer']:
        manufacturers[manuf['value']] = manuf['text']
    with open("manufacturers.json", "w") as manufs:
        json.dump(manufacturers, manufs)
    tasks_ = DbHandler.load_tasks()
    if tasks_ is None:
        return
    for id_, task in tasks_.items():
        task_info = models.Task(**task)
        asyncio.run_coroutine_threadsafe(schedule_task(task_info), asyncio.get_event_loop())


@app.get("/manufacturers")
async def get_manufacturers():
    logging.info(f"Getting manufacturer list")
    return manufs_unaltered


@app.get("/models/{manufacturer_id}")
async def get_models(manufacturer_id: str):
    logging.info(f"Getting models for manufacturer: {manufacturer_id}")
    # scraper = Scraper(cache_timeout_min=5)
    car_models = await Scraper.get_model(manufacturer_id)
    if 'data' not in car_models:
        return []
    return car_models['data']['model']


def extract_query_params(url: str) -> dict:
    # Extract query parameters from the URL
    params = dict(parse.parse_qsl(parse.urlsplit(url).query))
    return params


tasks: Dict[str, models.Task] = dict()
scheduled_task_events: Dict[str, threading.Event] = dict()


@app.get("/tasks", response_model=List[models.Task])
async def read_items():
    return [task for task in tasks.values()]


@app.get("/scrape")
async def scrape(url: str, response_model=List[CarDetails]):
    params = extract_query_params(url)
    scraper = Scraper(cache_timeout_min=30)
    results: List[CarDetails] = await scraper.scrape_criteria(params)
    return results


@app.get("/scrape_excel")
async def scrape_excel(url: str):
    params: dict = extract_query_params(url)
    scraper = Scraper(cache_timeout_min=30)
    results: List[CarDetails] = await scraper.scrape_criteria(params)
    df: pd.DataFrame = dump_to_excel_car_details(results)
    filename = "car_ads_"
    for param in params.values():
        filename += param + "_"
    filename = filename + ".xlsx"
    # return StreamingResponse(
    #     iter([df.to_csv(index=False)]),
    #     media_type="text/csv",
    #     headers={"Content-Disposition": f"attachment; filename=data.csv"})
    df.to_excel('car_ads.xlsx', index=False)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        df.to_excel(writer, index=False)

    return StreamingResponse(
        BytesIO(buffer.getvalue()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": f"attachment; filename={filename}"})


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
    mail_sender = EmailSender()
    db_handler = DbHandler(parse.urlsplit(tasks[task_id].title).query, mail_sender)
    results = scraper.run(params, loop)
    internal_info_logger.info(f"Recurrence task: {task_id}: {tasks[task_id]}")
    # update the next scrape time
    tasks[task_id].next_scrape_time = datetime.now() + timedelta(hours=tasks[task_id].repeat_interval)
    internal_info_logger.info(f'Updated next_scrape_time: {tasks[task_id].next_scrape_time}')
    db_handler.update_task(tasks[task_id])
    db_handler.handle_results(results)


def scrape_task(task_id: str, loop):
    params = extract_query_params(tasks[task_id].title)
    internal_info_logger.info(f'Scraping task: {tasks[task_id]}')
    internal_info_logger.info(f'created_at: {tasks[task_id].created_at}, '
                f'next_scrape_time: {tasks[task_id].next_scrape_time}')
    scraper = Scraper(cache_timeout_min=30)
    results: List[CarDetails] = scraper.run(params, loop)
    time_now = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")

    filename_json = f'json/car_ads_{task_id}' + time_now + '.json'
    directory = os.path.dirname(filename_json)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(filename_json, 'w', encoding='utf-8') as f1:
        json.dump({ad.id: ad.model_dump(mode='json') for ad in results}, f1, indent=4, ensure_ascii=False)
    mail_sender = EmailSender()
    db_handler = DbHandler(parse.urlsplit(tasks[task_id].title).query, mail_sender)
    if db_handler.collection_exists():
        db_handler.handle_results(results)
    else:
        db_handler.create_collection(results)
    # Do some work that only needs to happen once...
    return schedule.CancelJob


def search_by_model(car_list, target_value):
    for car in car_list:
        if car["value"] == target_value:
            return car["text"]
    return None  # Return None if the value is not found


# Update (PUT)
@app.put("/items/{item_id}", response_model=models.Task)
async def update_item(item_id: str, email: EmailStr, repeat_interval: int):
    task = tasks.get(item_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Item not found")
    task.mail = email
    task.repeat_interval = repeat_interval
    new_scrape_time = datetime.now() + timedelta(hours=repeat_interval)
    if task.next_scrape_time < new_scrape_time:
        task.next_scrape_time = datetime.now() + timedelta(hours=repeat_interval)
    else:
        task.next_scrape_time = new_scrape_time
    DbHandler.update_task(task)
    return task

@app.post("/tasks", response_model=models.Task)
async def create_item(email: EmailStr, url: str):
    params: dict = extract_query_params(url)

    if 'manufacturer' not in params or 'model' not in params or 'year' not in params or 'km' not in params:
        raise HTTPException(status_code=400, detail="Invalid URL")

    id_ = hashlib.sha256(url.encode()).hexdigest()
    if id_ in tasks:
        return tasks[id_]

    car_models = []
    car_models_dict = await get_models(params['manufacturer'])
    for car_model in params['model'].split(","):
        car_models.append(search_by_model(car_models_dict, car_model))

    repeat_interval_hours = 6
    task = models.Task(id=id_, title=url, mail=email,
                       created_at=datetime.now(),
                       next_scrape_time=datetime.now() + timedelta(hours=repeat_interval_hours),
                       repeat_interval=repeat_interval_hours,
                       manufacturer=manufacturers[params['manufacturer']],
                       car_models=car_models)
    # create task in database
    DbHandler.insert_task(task)
    await schedule_task(task)
    return task


async def schedule_task(task: models.Task, repeat_interval_hr=6):
    params: dict = extract_query_params(task.title)
    loop = asyncio.get_event_loop()
    schedule.every(1).seconds.do(scrape_task, task.id, loop)
    schedule.every(repeat_interval_hr).hours.do(recurrent_scrape, task.id, params, loop)
    event_: threading.Event = run_continuously()
    tasks[task.id] = task
    scheduled_task_events[task.id] = event_


@app.on_event("shutdown")
def shutdown_event():
    print("Application shutdown")
    for task in tasks.values():
        scheduled_task_events[task.id].set()
        scheduled_task_events.pop(task.id)
        print("Cleared task with task id: " + task.id)


@app.delete("/tasks/{task_id}")
async def delete_item(task_id: str):
    if task_id not in tasks:
        return {"message": f"Task: {task_id} not found"}
    task: models.Task = tasks.pop(task_id)
    # Stop the background thread
    scheduled_task_events[task_id].set()
    scheduled_task_events.pop(task_id)
    # delete from database
    DbHandler.delete_task(task_id)
    return {"message": f"Task: {task} deleted"}


def get_range(data: str) -> models.Range:
    # Split the data on the separator
    parts = data.split('-')
    parts = [int(part) for part in parts if part.isdigit()]
    parts = [part * -1 if part == 1 else part for part in parts]
    return models.Range(min=parts[0], max=parts[1])
