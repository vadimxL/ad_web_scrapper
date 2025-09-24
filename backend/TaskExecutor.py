from datetime import timedelta, datetime
from logging import Logger
from backend import models
from backend.email.email_sender import EmailSender
from backend.logger_setup import internal_info_logger
from backend.scraper import Scraper
from backend.notifier import Notifier

# from scraper import Scraper


class TaskExecutor:
    def __init__(self, logger: Logger):
        try:
            sender_email = EmailStr(os.getenv("SENDER_EMAIL"))
            sender_pw = os.getenv("EMAIL_PASSWORD")
            self._email_sender = EmailSender(sender_email, sender_pw)
        except Exception as e:
            internal_info_logger.error(f"Error initializing db: {e}")
        self.logger = logger

    def _recent_task(self, task: models.Task):
        return (datetime.now() - task.last_run) < timedelta(days=1)

    def run(self, task_id: str, logger: Logger):
        logger.info(f"Executing task: {task_id}")
        scraper = Scraper(cache_timeout_min=30, logger=logger)
        task: Optional[models.Task] = DbHandler.get_task(task_id)
        if task is None:
            logger.error(f"Task {task_id} not found")
            return
        if not task.active:
            logger.info(f"Task {task_id} is not active")
            return
        # mail_sender = EmailSender(task.mail)
        # db_handler =  DbHandler(task.title, mail_sender)
        results, _ = scraper.run(task.params)
        internal_info_logger.info(f"Recurrence task: {task_id}: {task}")
        task.last_run = datetime.now()
        self.db_handler.update_task(task)
        notifier = Notifier(email_sender, task.mail, internal_info_logger)
        if results:
            if self.db_handler.collection_exists() and self._recent_task(task):
                self.db_handler.handle_results(results, notifier)
            else:
                self.db_handler.create_collection(results, notifier)