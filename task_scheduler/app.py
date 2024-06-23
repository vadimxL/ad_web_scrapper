import asyncio
import atexit
import threading
import time
from typing import Dict
import schedule
import models
from db_handler import DbHandler
from logger_setup import internal_info_logger
from main import recurrent_scrape, extract_query_params
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
    print("Scheduling task", task.id, task.title)
    job = schedule.every(task.repeat_interval).hours.do(recurrent_scrape,
                                                      task_id=task.id,
                                                      loop=asyncio.get_event_loop())
    job.tag(task.id)
    return job

event_: threading.Event
async def run():
    global event_
    event_ = run_continuously()
    while True:
        tasks_ = DbHandler.load_tasks()
        if tasks_:
            for id_, task_dict in tasks_.items():
                task_ = models.Task(**task_dict)
                jobs = schedule.get_jobs(task_.id)
                if jobs:
                    print(f"Task {jobs[0]} already scheduled, next_run: {jobs[0].next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                    # User updated repeat_interval
                    if jobs[0].interval != task_.repeat_interval:
                        schedule.cancel_job(jobs[0])
                        scheduled_job: schedule.Job = schedule_task(task_)
                        threading.Thread(target=scheduled_job.run).start()
                        print(f"Rescheduling task {task_.id}, next_run: {jobs[0].next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                    continue
                scheduled_job: schedule.Job = schedule_task(task_)
                threading.Thread(target=scheduled_job.run).start()
        await asyncio.sleep(5)

def shutdown():
    print("Shutting down...")
    event_.set()
    schedule.clear()

if __name__ == '__main__':
    try:
        firebase_db.init_firebase_db()
    except Exception as e:
        print(f"Error initializing firebase db: {e}")
        exit(1)
    asyncio.run(run())
    atexit.register(shutdown)
