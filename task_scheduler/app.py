import asyncio
import atexit
import threading
import time
from typing import Dict
import schedule
import models
from db_handler import DbHandler
from logger_setup import internal_info_logger as logger
from main import execute
import firebase_db
scheduled_task_events: Dict[str, threading.Event] = dict()


def run_continuously(interval=1):
    """Continuously run, while executing pending jobs at each
    elapsed time interval.
    @return cease_continuous_run: threading. Event which can
    be set to cease continuous run. Please note that it is
    *intended behavior that run_continuously() does not run
    missed jobs*. For example, if you've registered a job that
    should run every minute and you set a continuous run
    interval of one hour then your job won't be run 60 times
    at each interval but only once.
    """
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run


def schedule_task(task: models.Task):
    logger.info(f"Scheduling task: {task.id=}, {task.title=}")
    job = schedule.every(task.repeat_interval).hours.do(execute,
                                                        task_id=task.id,
                                                        loop=asyncio.get_event_loop())
    job.tag(task.id)
    return job


def reschedule_task(task_: models.Task):
    jobs = schedule.get_jobs(task_.id)
    schedule.cancel_job(jobs[0])
    scheduled_job: schedule.Job = schedule_task(task_)
    threading.Thread(target=scheduled_job.run).start()
    logger.info(f"Rescheduling task {task_.id}, next_run: {scheduled_job.next_run.strftime('%Y-%m-%d %H:%M:%S')}")

def tasks_changed_listener(event):
    logger.info(f"Tasks changed, {event}")
    if event.event_type == 'patch':
        task: models.Task = DbHandler.get_task(event.path.lstrip('/'))
        if 'title' in event.data:
            reschedule_task(task)
        if 'repeat_interval' in event.data:
            reschedule_task(task)

event_: threading.Event
async def run():
    global event_
    event_ = run_continuously()
    DbHandler.create_listener(tasks_changed_listener)
    if tasks_ := DbHandler.load_tasks():
        for task_dict in tasks_.values():
            task_ = models.create_task_from_dict(task_dict)
            if task_.active:
                scheduled_job: schedule.Job = schedule_task(task_)
                threading.Thread(target=scheduled_job.run).start()
    while not event_.is_set():
        logger.info(f"Running scheduled tasks/jobs: {schedule.get_jobs()}")
        await asyncio.sleep(5)
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
