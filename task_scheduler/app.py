import asyncio
import atexit
import threading
import time
from datetime import timedelta, datetime
from random import randint
from typing import Dict, List
import schedule
import models
from db_handler import DbHandler
from logger_setup import internal_info_logger as logger
from main import execute_tasks
import firebase_db
scheduled_task_events: Dict[str, threading.Event] = dict()


def _run_task(task_id: str):
    time.sleep(randint(5, 30))  # sleep for a random time between 5 and 30 seconds
    logger.info(f"Running task {task_id}")
    execute_tasks(task_id)

def run_task(task_id: str):
    # Get the current date and time
    now = datetime.now()

    # Replace the hour, minute, second, and microsecond to set the time to 21:00
    today_at_22 = now.replace(hour=22, minute=0, second=0, microsecond=0)
    today_at_7 = now.replace(hour=7, minute=0, second=0, microsecond=0)

    if today_at_7 < now < today_at_22:
        # If the current time is between 8 AM and 9 PM, schedule the task for 9 PM
        threading.Thread(target=_run_task, args=(task_id,)).start()
    else:
        logger.info(f"Task {task_id} will be run tomorrow because it's not between 8 AM and 9 PM")



def tasks_changed_listener(event):
    logger.info(f"Tasks changed, {event.data=}, {event.path=}, {event.event_type=}")
    if event.event_type == 'patch':
        if event.data in ('title', 'repeat_interval', 'active'):
            task_id = event.path.lstrip('/')
            run_task(task_id)
    if event.event_type == 'put':
        if event.data is None: # task deleted or no tasks
            logger.info("All tasks deleted or not tasks found")
        elif event.path == '/': # all tasks
            for task_id, task_dict in event.data.items():
                run_task(task_id)
        elif len(event.path.split('/')) < 3: # single task added
            task_id = event.path.lstrip('/')
            run_task(task_id)
        else:
            split_path = event.path.split('/')
            task_id = split_path[1]
            prop = split_path[2]
            if prop in ('title', 'repeat_interval', 'active'):
                run_task(task_id)


event_: threading.Event
async def run():
    DbHandler.create_listener(tasks_changed_listener)
    global event_
    event_ = threading.Event()
    while not event_.is_set():
        tasks: List[models.Task] = DbHandler.get_tasks()
        for task in tasks:
            logger.info(f"Job id: {task.id}, "
                        f"last_run: {task.last_run}, "
                        f"next_run: {task.last_run + timedelta(hours=1)}, "
                        f"active: {task.active}, "
                        f"manufacturers: {task.manufacturers}, "
                        f"models: {task.car_models} ")
            await asyncio.sleep(0.1)
        await asyncio.sleep(timedelta(minutes=5).seconds)
    logger.info("Exiting run loop")

def shutdown():
    logger.info("Shutting down...")
    event_.set()
    schedule.clear()

if __name__ == '__main__':
    try:
        firebase_db.init_firebase_db()
    except Exception:
        logger.exception(f"Error initializing firebase db")
        exit(1)
    asyncio.run(run())
    atexit.register(shutdown)
