import asyncio
import atexit
import threading
import time
from datetime import timedelta, datetime
from random import randint
from typing import Dict, List
import models
from db_firestore_handler import FbDbHandler as DbHandler
from loguru import logger

scheduled_task_events: Dict[str, threading.Event] = dict()


class TaskScheduler:
    def __init__(self, task_cb: callable):
        self.event_ = threading.Event()
        self.task_cb = task_cb

    def _run_task(self, task_id: str):
        time.sleep(randint(30, 120))  # sleep for a random time between 5 and 30 seconds
        logger.info(f"Running task {task_id}")
        self.task_cb(task_id)

    def run_task(self, task_id: str):
        # Get the current date and time
        now = datetime.now()

        end_day = now.replace(hour=23, minute=59, second=0, microsecond=0)
        start_day = now.replace(hour=7, minute=0, second=0, microsecond=0)

        if start_day < now < end_day:
            threading.Thread(target=self._run_task, args=(task_id,)).start()
        else:
            logger.info(f"Task {task_id} will be run tomorrow because it's not between {start_day} AM and {end_day} PM")

    def tasks_changed_listener(self, doc_snapshot, changes, read_time):
        for doc in doc_snapshot:
            print(f"Received document snapshot: {doc.id}")
        """
                logger.info(f"Tasks changed, {event.data=}, {event.path=}, {event.event_type=}")
        if event.event_type == 'patch':
            if event.data in ('title', 'repeat_interval', 'active'):
                task_id = event.path.lstrip('/')
                self.run_task(task_id)
        if event.event_type == 'put':
            if event.data is None:  # task deleted or no tasks
                logger.info("All tasks deleted or not tasks found")
            elif event.path == '/':  # all tasks
                for task_id, task_dict in event.data.items():
                    self.run_task(task_id)
            elif len(event.path.split('/')) < 3:  # single task added
                task_id = event.path.lstrip('/')
                self.run_task(task_id)
            else:
                split_path = event.path.split('/')
                task_id = split_path[1]
                prop = split_path[2]
                if prop in ('title', 'repeat_interval', 'active'):
                    self.run_task(task_id)
        """

    def run(self):
        DbHandler.create_listener(self.tasks_changed_listener)
        while not self.event_.is_set():
            tasks: List[models.Task] = DbHandler.get_tasks()
            for task in tasks:
                logger.info(f"Job id: {task.id}, "
                            f"last_run: {task.last_run}, "
                            f"active: {task.active}, "
                            f"manufacturers: {task.manufacturers}, "
                            f"models: {task.car_models} ")
                time.sleep(0.1)
            time.sleep(timedelta(minutes=5).seconds)
        logger.info("Exiting run loop")

    def stop(self):
        logger.info("Shutting down...")
        self.event_.set()
