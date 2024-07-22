import asyncio
import hashlib

import firebase_admin
from firebase_admin import credentials

import json
import threading
from contextlib import asynccontextmanager
from enum import Enum
from io import BytesIO
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional
from urllib import parse
from pydantic import EmailStr
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from fastapi import FastAPI, HTTPException
from db_firestore_handler import FbDbHandler as DbHandler
from email_sender.email_sender import EmailSender
import models
from notifier import Notifier
from scheduler import TaskScheduler
from scraper import Scraper, BASE_URL
from loguru import logger

logger.add("scraper.log")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load firebase db
    try:
        cred = credentials.Certificate('adscraper.json')
        firebase_admin.initialize_app(cred)
    except Exception as e:
        logger.error(f"Error initializing firebase db: {e}")
    scheduler = TaskScheduler(execute_tasks)
    scheduler_thread = threading.Thread(target=scheduler.run).start()
    yield
    scheduler.stop()


manufacturers_en = {
    "21": "hyundai",
    "48": "kia",
    "19": "toyota",
    "37": "seat",
    "46": "peugeot",
    "40": "skoda",
    "27": "mazda",
    "41": "volkswagen",
    "17": "honda",
    "30": "mitsubishi",
}

app = FastAPI(lifespan=lifespan)

# Allow all origins with appropriate methods, headers, and credentials if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],  # You can specify specific methods (e.g., ["GET", "POST"])
    allow_headers=["*"],  # You can specify specific headers if needed
    expose_headers=["*"]
)


async def get_models(manufacturer_id: str):
    logger.info(f"Getting models for manufacturer: {manufacturer_id}")
    # scraper = Scraper(cache_timeout_min=5)
    car_models = await Scraper.get_model(manufacturer_id)
    if 'data' not in car_models:
        return []
    return car_models['data']['model']


@app.get("/submodels/{model_id}")
async def get_submodels(model_id: str):
    logger.info(f"Getting models for manufacturer: {model_id}")
    # scraper = Scraper(cache_timeout_min=5)
    car_models = await Scraper.get_model(model_id)
    if 'data' not in car_models:
        return []
    return car_models['data']['model']


def extract_query_params(url: str) -> dict:
    # Extract query parameters from the URL
    params = dict(parse.parse_qsl(parse.urlsplit(url).query))
    return params


def join_query_params(params: dict) -> str:
    # Join the dictionary of query parameters into a string without URL encoding
    return '&'.join(f"{key}={value}" for key, value in params.items())


@app.get("/tasks", response_model=List[models.Task])
async def read_items():
    tasks = DbHandler.load_tasks()
    return [task for task in tasks.values()]


@app.get("/scrape", response_model=List[models.AdDetails])
async def scrape(url: str):
    params: dict = extract_query_params(url)
    scraper = Scraper(cache_timeout_min=30)
    results: List[models.AdDetails] = await scraper.scrape_criteria(params)
    return results


def make_hyperlink(value):
    url_ = f"{BASE_URL}/item/{value}"
    hyperlink = '=HYPERLINK("%s", "%s")' % (url_, value)
    return hyperlink


def ads_to_df(ads_: List[models.AdDetails]) -> pd.DataFrame:
    ads: dict = {ad.id: ad.model_dump(mode='json') for ad in ads_}
    df = pd.json_normalize(ads.values())
    df['id'] = df['id'].apply(make_hyperlink)
    return df


@app.get("/archive")
async def archive():
    # db_handler = DbHandler(on_new_cb=lambda x: None, on_update_cb=lambda x: None, on_archive_cb=lambda x: None)
    # results: List[models.AdDetails] = db_handler.get_archive()
    archived = []
    with open("archive.json", "r") as f:
        results = json.load(f)

    for id_, ad in results.items():
        if "full_info" in ad:
            ad.pop("full_info")

    df = pd.json_normalize(results.values())
    df['id'] = df['id'].apply(make_hyperlink)
    filename = "archive.xlsx"
    df.to_excel(filename, index=False)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        df.to_excel(writer, index=False)

    return StreamingResponse(
        BytesIO(buffer.getvalue()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.get("/scrape_excel")
async def scrape_excel(url: str):
    params: dict = extract_query_params(url)
    scraper = Scraper(cache_timeout_min=30)
    results: List[models.AdDetails] = await scraper.scrape_criteria(params)

    df: pd.DataFrame = ads_to_df(results)
    filename = "car_ads_"
    for param in params.values():
        filename += param + "_"
    # filename = filename + ".xlsx"
    filename = filename.replace(",", "_") + ".xlsx"

    df.to_excel('car_ads.xlsx', index=False)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        df.to_excel(writer, index=False)

    return StreamingResponse(
        BytesIO(buffer.getvalue()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": f"attachment; filename={filename}"})


def execute_tasks(task_id: str):
    logger.info(f"Executing task: {task_id}")
    scraper = Scraper(cache_timeout_min=30)
    task = DbHandler.get_task(task_id)
    mail_sender = EmailSender(task.mail, log_only=True)
    if task is None:
        logger.error(f"Task {task_id} not found")
        return
    if not task.active:
        logger.info(f"Task {task_id} is not active")
        return
    notifier = Notifier(mail_sender)
    db_handler = DbHandler(on_new_cb=notifier.notify_new_ad,
                           on_update_cb=notifier.notify_update_ad,
                           on_archive_cb=notifier.notify_archived)
    results, _ = scraper.run(task.params)
    logger.info(f"Recurrence task: {task_id}: {task}")
    task.last_run = datetime.now()
    db_handler.update_task(task)
    if results:
        if db_handler.collection_exists() and recent_task(task):
            logger.info(f"Handling results for task: {task_id}")
            db_handler.handle_results(results, task)
        else:
            logger.info(f"Creating collection for task: {task_id}")
            db_handler.create_collection(results)


def recent_task(task: models.Task):
    return (datetime.now() - task.last_run) < timedelta(days=1)


# Update (PUT)
@app.put("/tasks/{task_id}", response_model=models.Task)
async def update_task(task_id: str, email: Optional[EmailStr] = None, repeat_interval: Optional[int] = None):
    task = DbHandler.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if email is not None:
        task.mail = email
    if repeat_interval is not None:
        task.repeat_interval = repeat_interval
    DbHandler.update_task(task)
    return task


@app.get("/run")
async def run_tasks():
    """
    Run all tasks
    and Scrape the data
    """
    tasks = DbHandler.load_tasks()
    for id_, task_dict in tasks.items():
        task_ = models.create_task_from_dict(task_dict)
        loop = asyncio.get_event_loop()
        threading.Thread(target=execute_tasks, args=(task_.id,)).start()
    return {"message": "All tasks run successfully"}


@app.post("/tasks", response_model=models.Task)
async def create_task(email: EmailStr, url: str):
    """
    Create a new task
    """
    params: dict = extract_query_params(url)

    if 'manufacturer' not in params or 'model' not in params or 'year' not in params or 'km' not in params:
        raise HTTPException(status_code=400, detail="Invalid URL")

    # id_ = hashlib.sha256(url.encode()).hexdigest()
    id_ = hashlib.md5(url.encode()).hexdigest()[0:12]
    task = DbHandler.get_task(id_)
    if task is not None:
        raise HTTPException(status_code=400, detail="Task already exists")

    car_manufacturers, car_models, car_submodels = await Scraper.get_meta(params['manufacturer'],
                                                                          params.get('model', ""),
                                                                          params.get('subModel', ""))
    car_manufacturers_en = [manufacturers_en[manufacturer] for manufacturer in params['manufacturer'].split(",")]
    title_params: dict = params.copy()
    title_params['manufacturer'] = str.join(",", car_manufacturers_en)
    title = join_query_params(title_params)
    task = models.Task(id=id_, title=title, mail=email,
                       params=params,
                       created_at=datetime.now(),
                       last_run=datetime.now(),
                       manufacturers=car_manufacturers,
                       active=True,
                       car_models=car_models,
                       car_submodels=car_submodels)
    # create task in database
    DbHandler.insert_task(task)
    return task


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """
    Delete a task
    """
    task: models.Task = DbHandler.get_task(task_id)
    if not task:
        return {"message": f"Task: {task_id} not found"}
    DbHandler.delete_task(task_id)
    return {"message": f"Task: {task} deleted"}


def get_range(data: str) -> models.Range:
    # Split the data on the separator
    parts = data.split('-')
    parts = [int(part) for part in parts if part.isdigit()]
    parts = [part * -1 if part == 1 else part for part in parts]
    return models.Range(min=parts[0], max=parts[1])
