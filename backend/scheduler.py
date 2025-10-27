import threading
from datetime import datetime, timedelta
from logging import Logger
from random import randint
from typing import Dict, List, Optional

from firebase_admin.db import Event

from backend import models
from backend.config import SENDER_EMAIL, SENDER_EMAIL_PW
from backend.db.db_handler import DbHandler
from backend.email.email_sender import EmailSender
from backend.notifier import Notifier
from backend.scraper import Scraper

scheduled_task_events: Dict[str, threading.Event] = dict()


class TaskScheduler:
    def __init__(self, logger: Logger, db_handler: DbHandler):
        self.event_ = threading.Event()
        self._logger = logger
        self._task_threads: list[threading.Thread] = []  # track spawned task threads
        self._listener = None  # firebase listener (event source)
        self._db_handler = db_handler

    def _recent_task(self, task: models.Task):
        return (datetime.now() - task.last_run) < timedelta(days=1)

    def _execute_task(self, task_id: str):
        self._logger.info(f"Executing task: {task_id}")
        scraper = Scraper(cache_timeout_min=30, logger=self._logger)
        task: Optional[models.Task] = self._db_handler.get_task(task_id)
        if task is None:
            self._logger.error(f"Task {task_id} not found")
            return
        if not task.active:
            self._logger.info(f"Task {task_id} is not active")
            return
        results, _ = scraper.run(task.params)
        self._logger.info(f"Recurrence task: {task_id}: {task}")
        task.last_run = datetime.now()
        self._db_handler.update_task(task)
        mail_sender = EmailSender(SENDER_EMAIL, SENDER_EMAIL_PW)
        notifier = Notifier(mail_sender, [task.mail], self._logger)
        if results:
            if self._db_handler.collection_exists(task.title) and self._recent_task(task):
                self._db_handler.handle_results(results, task.title, notifier)
            else:
                self._db_handler.create_collection(task.title, results)

    def _run_task(self, task_id: str):
        # Use cancellable wait instead of raw sleep so shutdown is responsive
        delay = randint(30, 120)
        if self.event_.wait(delay):  # returns True if event set during wait
            self._logger.info(f"Cancelled task {task_id} before execution (shutdown)")
            return
        if self.event_.is_set():
            return
        self._logger.info(f"Running task {task_id}")
        try:
            self._execute_task(task_id)
        except Exception:
            self._logger.exception(f"Error running task {task_id}")

    def run_task(self, task_id: str):
        now = datetime.now()
        today_hour_end = now.replace(hour=23, minute=59, second=0, microsecond=0)
        today_hour_start = now.replace(hour=6, minute=0, second=0, microsecond=0)

        if today_hour_start < now < today_hour_end:
            t = threading.Thread(target=self._run_task, args=(task_id,), daemon=True)
            t.start()
            self._task_threads.append(t)
        else:
            self._logger.info(f"Time now: {now}, Task {task_id} will be run tomorrow because it's not between 6 AM and midnight")

    def tasks_changed_listener(self, event: Event) -> None:
        self._logger.info(f"Tasks changed, event type: {event.event_type}")
        self._logger.info(f"Tasks changed, event path: {event.path=}")
        self._logger.info(f"Tasks changed, event data: {event.data=}")
        if event.event_type == 'patch':
            return
        if event.event_type == 'put':
            if event.data is None:  # task deleted or no tasks
                self._logger.info("All tasks deleted or no tasks found")
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
        self._listener = self._db_handler.create_listener(self.tasks_changed_listener)
        self._logger.info("Scheduler started")
        # Main loop checks for stop signal frequently
        while not self.event_.is_set():
            tasks: List[models.Task] = self._db_handler.get_tasks()
            for task in tasks:
                self._logger.info(
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
        self._logger.info("Exiting run loop")

    def stop(self):
        self._logger.info("Shutting down...")
        self.event_.set()
        # Close firebase listener if present
        try:
            if self._listener and hasattr(self._listener, 'close'):
                self._listener.close()
                self._logger.info("Firebase listener closed")
        except Exception:
            self._logger.exception("Error closing firebase listener")
        # Join spawned task threads briefly
        for t in list(self._task_threads):
            if t.is_alive():
                t.join(timeout=2)
        self._logger.info("All task threads joined or timed out")