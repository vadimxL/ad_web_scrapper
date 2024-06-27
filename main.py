import asyncio
import hashlib
import logging
import threading
from asyncio import AbstractEventLoop
from io import BytesIO
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib import parse
from pydantic import EmailStr
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
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

@app.get("/submodels/{model_id}")
async def get_submodels(model_id: str):
    logging.info(f"Getting models for manufacturer: {model_id}")
    # scraper = Scraper(cache_timeout_min=5)
    car_models = await Scraper.get_model(model_id)
    if 'data' not in car_models:
        return []
    return car_models['data']['model']


def extract_query_params(url: str) -> dict:
    # Extract query parameters from the URL
    params = dict(parse.parse_qsl(parse.urlsplit(url).query))
    return params


@app.get("/tasks", response_model=List[models.Task])
async def read_items():
    tasks = DbHandler.load_tasks()
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
    # filename = filename + ".xlsx"
    filename = filename.replace(",", "_") + ".xlsx"

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


def execute_tasks(task_id: str):
    internal_info_logger.info(f"Executing task: {task_id}")
    scraper = Scraper(cache_timeout_min=30)
    task = DbHandler.get_task(task_id)
    mail_sender = EmailSender(task.mail)
    if task is None:
        internal_info_logger.error(f"Task {task_id} not found")
        return
    db_handler = DbHandler(parse.urlsplit(task.title).query, mail_sender)
    results: List[CarDetails] = scraper.run(extract_query_params(task.title))
    internal_info_logger.info(f"Recurrence task: {task_id}: {task}")
    # update the next scrape time
    task.last_scrape_time = datetime.now()
    task.next_scrape_time = datetime.now() + timedelta(hours=task.repeat_interval)
    db_handler.update_task(task)
    if results:
        if db_handler.collection_exists() and recent_task(task):
            db_handler.handle_results(results)
        else:
            db_handler.create_collection(results)


def recent_task(task: models.Task):
    return (datetime.now() - task.last_scrape_time) < timedelta(days=1)


# Update (PUT)
@app.put("/tasks/{task_id}", response_model=models.Task)
async def update_task(task_id: str, email: Optional[EmailStr] = None, repeat_interval: Optional[int] = None,
                      title: Optional[str] = None):
    task = DbHandler.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if email is not None:
        task.mail = email
    if repeat_interval is not None:
        task.repeat_interval = repeat_interval
    if title is not None:
        task.title = title
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

    id_ = hashlib.sha256(url.encode()).hexdigest()
    task = DbHandler.get_task(id_)
    if task is not None:
        raise HTTPException(status_code=400, detail="Task already exists")

    car_manufacturers = []
    for manuf in params['manufacturer'].split(","):
        car_manufacturers.append(manufacturers[manuf])

    car_models, car_submodels = await Scraper.get_meta(params['manufacturer'])

    repeat_interval_hours = 6
    task = models.Task(id=id_, title=url, mail=email,
                       created_at=datetime.now(),
                       next_scrape_time=datetime.now() + timedelta(hours=repeat_interval_hours),
                       last_scrape_time=datetime.now(),
                       repeat_interval=repeat_interval_hours,
                       manufacturers=car_manufacturers,
                       active=False,
                       car_models=car_models,
                       car_submodels=car_submodels)
    # create task in database
    DbHandler.insert_task(task)
    return task


@app.on_event("shutdown")
def shutdown_event():
    print("Application shutdown")


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
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
