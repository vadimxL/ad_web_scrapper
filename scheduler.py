import asyncio
import atexit
import threading
import time
from datetime import timedelta, datetime
from random import randint
from typing import Dict, List
import models
from db_handler import DbHandler
from logger_setup import internal_info_logger as logger
import firebase_db

scheduled_task_events: Dict[str, threading.Event] = dict()


class TaskScheduler:
    def __init__(self, task_cb: callable):
        self.event_ = threading.Event()
        self.task_cb = task_cb
        self._task_threads: list[threading.Thread] = []  # track spawned task threads

    def _run_task(self, task_id: str):
        # Use cancellable wait instead of raw sleep so shutdown is responsive
        delay = randint(30, 120)
        if self.event_.wait(delay):  # returns True if event set during wait
            logger.info(f"Cancelled task {task_id} before execution (shutdown)")
            return
        if self.event_.is_set():
            return
        logger.info(f"Running task {task_id}")
        try:
            self.task_cb(task_id)
        except Exception:
            logger.exception(f"Error running task {task_id}")

    def run_task(self, task_id: str):
        now = datetime.now()
        today_hour_end = now.replace(hour=23, minute=59, second=0, microsecond=0)
        today_hour_start = now.replace(hour=6, minute=0, second=0, microsecond=0)

        if today_hour_start < now < today_hour_end:
            t = threading.Thread(target=self._run_task, args=(task_id,), daemon=True)
            t.start()
            self._task_threads.append(t)
        else:
            logger.info(f"Time now: {now}, Task {task_id} will be run tomorrow because it's not between 6 AM and midnight")

    def tasks_changed_listener(self, event):
        logger.info(f"Tasks changed, {event.data=}, {event.path=}, {event.event_type=}")
        if event.event_type == 'patch':
            return
        if event.event_type == 'put':
            if event.data is None:  # task deleted or no tasks
                logger.info("All tasks deleted or no tasks found")
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

    def run(self):
        DbHandler.create_listener(self.tasks_changed_listener)
        logger.info("Scheduler started")
        # Main loop checks for stop signal frequently
        while not self.event_.is_set():
            tasks: List[models.Task] = DbHandler.get_tasks()
            for task in tasks:
                logger.info(
                    f"Job id: {task.id}, "
                    f"Time now: {datetime.now().strftime('%m/%d/%Y %H:%M:%S')}, "
                    f"last_run: {task.last_run.strftime('%m/%d/%Y %H:%M:%S')}, "
                    f"next_run: {(task.last_run + timedelta(hours=1)).strftime('%m/%d/%Y %H:%M:%S')}, "
                    f"active: {task.active}, "
                    f"manufacturers: {task.manufacturers}, "
                    f"models: {task.car_models} "
                )
                if self.event_.wait(0.05):  # small responsive wait
                    break
            # Wait up to 5 minutes, but wake early if stopping
            if self.event_.wait(300):
                break
        logger.info("Exiting run loop")

    def stop(self):
        logger.info("Shutting down...")
        self.event_.set()
        # Join spawned task threads briefly
        for t in list(self._task_threads):
            if t.is_alive():
                t.join(timeout=2)
        logger.info("All task threads joined or timed out")


if __name__ == '__main__':
    try:
        firebase_db.init_firebase_db()
    except Exception:
        logger.exception("Error initializing firebase db")
        exit(1)
    # Provide a no-op task callback when running standalone
    task_scheduler = TaskScheduler(lambda _tid: logger.info(f"(Standalone) would run task {_tid}"))
    threading.Thread(target=task_scheduler.run, daemon=True).start()
    atexit.register(task_scheduler.stop)
