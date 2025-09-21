from datetime import timedelta, datetime

import models
from backend.db.db_handler import DbHandler
from email_sender.email_sender import EmailSender
from logger_setup import internal_info_logger
from scraper import Scraper


class TaskExecutor:
    @staticmethod
    def recent_task(task: models.Task):
        return (datetime.now() - task.last_run) < timedelta(days=1)

    @staticmethod
    def run(task_id: str):
        internal_info_logger.info(f"Executing task: {task_id}")
        scraper = Scraper(cache_timeout_min=30)
        task = DbHandler.get_task(task_id)
        if task is None:
            internal_info_logger.error(f"Task {task_id} not found")
            return
        if not task.active:
            internal_info_logger.info(f"Task {task_id} is not active")
            return
        mail_sender = EmailSender(task.mail)
        db_handler = DbHandler(task.title, mail_sender)
        results, _ = scraper.run(task.params)
        internal_info_logger.info(f"Recurrence task: {task_id}: {task}")
        task.last_run = datetime.now()
        db_handler.update_task(task)
        if results:
            if db_handler.collection_exists() and TaskExecutor.recent_task(task):
                db_handler.handle_results(results)
            else:
                db_handler.create_collection(results)