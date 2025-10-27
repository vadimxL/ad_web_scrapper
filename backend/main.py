import hashlib
import logging
import os
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, List, Optional, Tuple

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel  # removed EmailStr
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from backend import models
from backend.auth import create_user_repo, get_current_user, set_user_repo
from backend.auth import router as auth_router
from backend.criteria_model import html_task_created
from backend.db.database import Database
from backend.db.db_handler import DbHandler
from backend.db.firebase_config import FirebaseConfig
from backend.email.email_sender import EmailSender
from backend.logger_setup import internal_info_logger
from backend.scheduler import TaskScheduler
from backend.scraper import Scraper
from backend.utils import extract_query_params, join_query_params


def get_db_handler() -> DbHandler:
    return app.state.db_handler  # type: ignore[return-value]

DBHandlerDep = Annotated[DbHandler, Depends(get_db_handler)]
UserDep = Annotated[dict, Depends(get_current_user)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database explicitly with config (non-singleton)
    cfg = FirebaseConfig.from_config_module()
    shared_db = Database(cfg)
    app.state.database = shared_db

    # Initialize auth user repo with shared DB (Firebase if configured)
    user_repo = create_user_repo(shared_db)
    set_user_repo(user_repo)

    db_handler = DbHandler(db=shared_db, logger=internal_info_logger)
    scheduler = TaskScheduler(internal_info_logger, db_handler=db_handler)
    scheduler_thread = threading.Thread(target=scheduler.run, name="task-scheduler")
    scheduler_thread.start()
    app.state.db_handler = db_handler
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

# Configure CORS with explicit origins (wildcard + credentials is invalid)
_frontend_origins_env = os.getenv("FRONTEND_ORIGINS", "")
if _frontend_origins_env:
    _allowed_origins = [o.strip() for o in _frontend_origins_env.split(",") if o.strip()]
else:
    _allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://172.22.122.196:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],  # allow all methods so preflight (OPTIONS) passes
    allow_headers=["*"],  # or specify e.g. ["Authorization", "Content-Type"]
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
async def read_items(user: UserDep, db_handler: DBHandlerDep):
    tasks = db_handler.load_tasks()
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
        [manufacturers_in_en[int(manufacturer)] for manufacturer in params['manufacturer'].split(",")]
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
                      user: UserDep,
                      db_handler: DBHandlerDep,
                      km_min: Annotated[Optional[int], Query(title="Min value of mileage", ge=-1)] = None,
                      km_max: Annotated[Optional[int], Query(title="Max value of mileage", le=200000)] = None) -> models.Task:
    manufacturers_en: dict = await get_manufacturers_en()
    task = db_handler.get_task(task_id)
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

    db_handler.update_task(task)
    return task

# Core logic extracted to avoid calling route function directly
async def _create_task_logic(email: str, url: str, user: dict, db_handler: DbHandler) -> models.Task:
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
    task = db_handler.get_task(id_)
    if task is not None:
        raise HTTPException(status_code=400, detail="Task already exists")

    car_manufacturers, car_models, car_submodels = await Scraper.get_meta(params['manufacturer'],
                                                                          params.get('model', ""),
                                                                          params.get('subModel', ""))
    title = create_title(params, manufacturers_en)
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
    db_handler.insert_task(task)

    # Send confirmation email with alert details
    try:
        sender_email = os.getenv("SENDER_EMAIL", "")
        sender_pw = os.getenv("EMAIL_PASSWORD", "")
        mail_sender = EmailSender(sender_email, sender_pw)
        message = html_task_created(task)
        internal_info_logger.info(f"Sending task creation email to {task.mail}")
        mail_sender.send(message, [task.mail], f"✅ Alert created: {task.title}")
    except Exception as e:
        internal_info_logger.error(f"Error sending task creation email: {e}")

    return task


@app.post("/tasks", response_model=models.Task)
async def create_task(email: str, url: str, user: UserDep, db_handler: DBHandlerDep) -> models.Task:
    return await _create_task_logic(email, url, user, db_handler)


class UITask(BaseModel):
    email: str
    km_start: int
    km_end: int
    manufacturer: str
    model: str
    year_start: int
    year_end: int
    engine_vol_start: int
    engine_vol_end: int
    seller_type: str = 'all'  # NEW optional field from UI



@app.post("/v2/tasks", response_model=models.Task)
async def create_task_v2(ui_task: UITask, user: UserDep, db_handler: DBHandlerDep):
    # Log received seller_type (for now we only log it; not stored in params URL)
    internal_info_logger.info(f"Received seller_type={ui_task.seller_type} for new task (email={ui_task.email})")
    url = (f"?manufacturer={ui_task.manufacturer}&model={ui_task.model}&year={ui_task.year_start}-{ui_task.year_end}"
           f"&km={ui_task.km_start}-{ui_task.km_end}"
           f"&engineval={ui_task.engine_vol_start}-{ui_task.engine_vol_end}")  # seller_type intentionally NOT added
    return await _create_task_logic(ui_task.email, url, user, db_handler)


@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user: UserDep, db_handler: DBHandlerDep):
    """
    Delete a task, archive it (max 5 per user), and notify via email.
    """
    task: models.Task = db_handler.get_task(task_id)
    if not task:
        return {"message": f"Task: {task_id} not found"}
    if task.owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")

    # Attempt to send deletion notification email before deleting.
    try:
        sender_email = os.getenv("SENDER_EMAIL", "")
        sender_pw = os.getenv("EMAIL_PASSWORD", "")
        mail_sender = EmailSender(sender_email, sender_pw)
        subject = f"🗑️ Alert deleted: {task.title}"
        body = (
            f"<p>The alert <strong>{task.title}</strong> was deleted.</p>"
            f"<p>If this was a mistake you can recreate it from the criteria form or history.</p>"
        )
        internal_info_logger.info(f"Sending task deletion email to {task.mail}")
        mail_sender.send(body, [task.mail], subject)
    except Exception as e:
        internal_info_logger.error(f"Error sending task deletion email: {e}")

    # Archive then delete
    db_handler.add_deleted_task(task)
    db_handler.delete_task(task_id)
    return {"message": f"Task: {task.title} deleted"}

@app.get("/deleted_tasks", response_model=List[models.Task])
async def list_deleted_tasks(user: UserDep, db_handler: DBHandlerDep) -> List[models.Task]:
    """Return up to last 5 deleted tasks for the authenticated user."""
    return db_handler.get_deleted_tasks(user["id"])


def get_range(data: str) -> models.Range:
    # Split the data on the separator
    parts = data.split('-')
    parts = [int(part) for part in parts if part.isdigit()]
    parts = [part * -1 if part == 1 else part for part in parts]
    return models.Range(min=parts[0], max=parts[1])


@app.post("/debug/clear_tasks")
def clear_tasks_debug(db_handler: DBHandlerDep):
    removed_tasks = db_handler.clear_all_tasks()
    return {"message": f"All tasks have been removed (debug route). {len(removed_tasks)} tasks deleted."}
