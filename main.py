import asyncio
import hashlib
import logging
import threading
import os
from enum import Enum

import models
import firebase_db
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Annotated
from urllib import parse
from enum import Enum
from pydantic import EmailStr, BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI, HTTPException, Query, Depends

from TaskExecutor import TaskExecutor
from db_handler import DbHandler
from email_sender.email_sender import EmailSender
from logger_setup import internal_info_logger
from scheduler import TaskScheduler
from scraper import Scraper
from utils import join_query_params, extract_query_params
from criteria_model import html_task_created
from auth import router as auth_router, get_current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load firebase db
    try:
        firebase_db.init_firebase_db()
    except Exception as e:
        internal_info_logger.error(f"Error initializing firebase db: {e}")
    task_executor = TaskExecutor()
    scheduler = TaskScheduler(task_executor.run)
    scheduler_thread = threading.Thread(target=scheduler.run, name="task-scheduler")
    scheduler_thread.start()
    try:
        yield
    finally:
        scheduler.stop()
        scheduler_thread.join(timeout=3.0)
        if scheduler_thread.is_alive():
            internal_info_logger.warning("Scheduler thread did not exit after join timeout")
        else:
            internal_info_logger.info("Scheduler thread exited cleanly")

async def get_manufacturers_en() -> dict:
    manufacturers_en = {}
    catalog: dict = await Scraper.get_vehicles_car_catalog()
    if 'data' not in catalog:
        return manufacturers_en
    manufacturers = catalog['data']['manufacturer']
    for manufacturer in manufacturers:
        manufacturers_en[manufacturer['id']] = manufacturer['engTitle']
    return manufacturers_en

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

# Server-side session middleware (cookie-based)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "change-this-secret"),
    same_site="lax",
)

# Include authentication routes
app.include_router(auth_router, prefix="/auth")


@app.get("/models/{manufacturer_id}")
async def get_models(manufacturer_id: str):
    logging.info(f"Getting models for manufacturer: {manufacturer_id}")
    car_models = await Scraper.get_model(manufacturer_id)
    if 'data' not in car_models:
        return []
    return car_models['data']['model']

@app.get("/manufacturers")
async def get_manufacturers():
    manufacturers = await Scraper.get_manufacturers()
    logging.info(f"Getting manufacturers, {manufacturers}")
    if 'data' not in manufacturers:
        return []
    return manufacturers['data']['manufacturer']

@app.get("/vehicles-car-catalog")
async def get_vehicles_car_catalog():
    catalog: dict = await Scraper.get_vehicles_car_catalog()
    logging.info(f"Getting vehicles-car-catalog, {catalog}")
    if 'data' not in catalog:
        return []
    return catalog['data']['manufacturer']


@app.get("/submodels/{model_id}")
async def get_submodels(model_id: str):
    logging.info(f"Getting models for manufacturer: {model_id}")
    # scraper = Scraper(cache_timeout_min=5)
    car_models = await Scraper.get_submodel(model_id)
    if 'data' not in car_models:
        return []
    return car_models['data']['subModel']

@app.get("/tasks", response_model=List[models.Task])
async def read_items(user: dict = Depends(get_current_user)):
    tasks = DbHandler.load_tasks()
    if tasks is None:
        return []
    # Filter tasks by owner_id
    return [
        models.create_task_from_dict(task_dict)
        for task_dict in tasks.values()
        if task_dict.get("owner_id") == user["id"]
    ]



def create_title(params: dict, manufacturers_in_en: dict) -> str:
    car_manufacturers_en: list = \
        [manufacturers_in_en[manufacturer] for manufacturer in params['manufacturer'].split(",")]
    title_params: dict = params.copy()
    title_params['manufacturer'] = str.join(",", car_manufacturers_en)
    title = join_query_params(title_params)
    print(f"Title params: {title}")
    return title


def parse_km_range(km_str: str) -> Tuple[int, int]:
    params_km_start: int = -1
    params_km_end: int = -1
    split_km: list = km_str.split("-")
    if len(split_km) == 4:  # -x--y
        params_km_start = -1 * int(split_km[1])
        params_km_end = -1 * int(split_km[3])
    if len(split_km) == 3 and split_km[0]:  # x--y
        params_km_start = int(split_km[0])
        params_km_end = -1 * int(split_km[2])
    if len(split_km) == 3 and not split_km[0]:  # -x-y
        params_km_start = -1 * int(split_km[1])
        params_km_end = int(split_km[2])
    if len(split_km) == 2:  # x-y
        params_km_start = int(split_km[0])
        params_km_end = int(split_km[1])
    return params_km_start, params_km_end


# Update (PUT)
@app.put("/tasks/{task_id}", response_model=models.Task)
async def update_task(task_id: str,
                      km_min: Annotated[Optional[int], Query(title="Min value of mileage", ge=-1)] = None,
                      km_max: Annotated[Optional[int], Query(title="Max value of mileage", le=200000)] = None,
                      user: dict = Depends(get_current_user)):
    manufacturers_en: dict = await get_manufacturers_en()
    task = DbHandler.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to modify this task")

    # Always set the task email from the authenticated user
    task.mail = user["email"]

    if "km" not in task.title:
        raise HTTPException(status_code=400, detail="Task does not have km range")

    params_km_start, params_km_end = parse_km_range(task.params['km'])

    if km_min is not None:
        task.params['km'] = f"{km_min}-{params_km_end}"
        task.title = create_title(task.params, manufacturers_en)
    if km_max is not None:
        task.params['km'] = f"{params_km_start}-{km_max}"
        task.title = create_title(task.params, manufacturers_en)

    DbHandler.update_task(task)
    return task


@app.get("/run")
async def run_tasks():
    """
    Run all tasks
    and Scrape the data
    """
    tasks = DbHandler.load_tasks()
    if tasks is None:
        return {"message": "No tasks found"}
    for id_, task_dict in tasks.items():
        task_ = models.create_task_from_dict(task_dict)
        loop = asyncio.get_event_loop()
        threading.Thread(target=TaskExecutor.run, args=(task_.id,)).start()
    return {"message": "All tasks run successfully"}


@app.post("/tasks", response_model=models.Task)
async def create_task(email: EmailStr, url: str, user: dict = Depends(get_current_user)) -> models.Task:
    """
    Create a new task
    """
    params: dict = extract_query_params(url)
    manufacturers_en: dict = await get_manufacturers_en()

    required_params = ['manufacturer', 'year', 'km'] # model
    missing_params = [param for param in required_params if param not in params or not params[param].strip()]
    if missing_params:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL, missing or empty required parameters: {', '.join(missing_params)}"
        )

    # id_ = hashlib.sha256(url.encode()).hexdigest()
    id_ = hashlib.md5(url.encode()).hexdigest()[0:12]
    task = DbHandler.get_task(id_)
    if task is not None:
        raise HTTPException(status_code=400, detail="Task already exists")

    car_manufacturers, car_models, car_submodels = await Scraper.get_meta(params['manufacturer'],
                                                                          params.get('model', ""),
                                                                          params.get('subModel', ""))
    title = create_title(params, manufacturers_en)
    print(f"Title params: {title}")
    task = models.Task(id=id_, title=title, mail=email,
                      params=params,
                      created_at=datetime.now(),
                      last_run=datetime.now(),
                      manufacturers=car_manufacturers,
                      active=True,
                      car_models=car_models,
                      car_submodels=car_submodels,
                      owner_id=user["id"])
    # create task in database
    DbHandler.insert_task(task)

    # Send confirmation email with alert details
    try:
        mail_sender = EmailSender(task.mail)
        message = html_task_created(task)
        internal_info_logger.info(f"Sending task creation email to {task.mail}")
        mail_sender.send(message, f"✅ Alert created: {task.title}")
    except Exception as e:
        internal_info_logger.error(f"Error sending task creation email: {e}")

    return task


class UITask(BaseModel):
    email: EmailStr
    km_start: int
    km_end: int
    manufacturer: str
    model: str
    year_start: int
    year_end: int



@app.post("/v2/tasks", response_model=models.Task)
async def create_task_v2(ui_task: UITask, user: dict = Depends(get_current_user)):
    url = f"?manufacturer={ui_task.manufacturer}&model={ui_task.model}&year={ui_task.year_start}-{ui_task.year_end}&km={ui_task.km_start}-{ui_task.km_end}"
    t: models.Task = await create_task(ui_task.email, url, user)
    return t


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user: dict = Depends(get_current_user)):
    """
    Delete a task
    """
    task: models.Task = DbHandler.get_task(task_id)
    if not task:
        return {"message": f"Task: {task_id} not found"}
    if task.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")
    DbHandler.delete_task(task_id)
    return {"message": f"Task: {task} deleted"}


def get_range(data: str) -> models.Range:
    # Split the data on the separator
    parts = data.split('-')
    parts = [int(part) for part in parts if part.isdigit()]
    parts = [part * -1 if part == 1 else part for part in parts]
    return models.Range(min=parts[0], max=parts[1])


@app.post("/debug/clear_tasks")
def clear_tasks_debug():
    removed_tasks = DbHandler.clear_all_tasks()
    return {"message": f"All tasks have been removed (debug route). {len(removed_tasks)} tasks deleted."}


