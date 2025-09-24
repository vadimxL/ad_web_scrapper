import json
from logging import Logger
from typing import List, Dict, Optional
from backend import models
from backend.car_details import CarDetails
from backend.criteria_model import html_criteria_mail
from backend.db.database import Database
from backend.notifier import Notifier


class DbHandler:
    ref_path = "cars"
    ref_path_sold = "sold_cars"

    def __init__(self, user_path: str, db: Database, logger: Logger):
        self.user_path = user_path
        self.sold_path = f'{self.ref_path_sold}/{self.user_path}'
        self._db: Database = db
        self._logger = logger

    def insert_task(self, task: models.Task):
        task_dict = task.model_dump(mode='json')
        self._db.reference('tasks').child(task.id).set(task_dict)
        self._logger.info(f"Task {task.id} is created successfully, {task}")

    def get_task(self, task_id: str) -> models.Task:
        task_dict: Dict = self._db.reference('tasks').child(task_id).get()
        if task_dict is None:
            return None
        task = models.create_task_from_dict(task_dict)
        return task

    def get_tasks(self) -> List[models.Task]:
        tasks_list = []
        tasks: Dict = self._db.reference('tasks').get()
        if tasks is None:
            return tasks_list
        for task_id, task_dict in tasks.items():
            tasks_list.append(models.create_task_from_dict(task_dict))
        return tasks_list

    def create_listener(self, callback):
        ref = self._db.reference('tasks')
        listener = ref.listen(callback)
        return listener

    def update_task(self, task: models.Task):
        task_dict = task.model_dump(mode='json')
        self._db.reference('tasks').child(task.id).update(task_dict)
        self._logger.info(f"Task {task.id} is updated successfully, {task}")

    def delete_task(self, task_id: str) -> models.Task:
        self._db.reference('tasks').child(task_id).delete()

    def load_tasks(self) -> Optional[Dict]:
        tasks = self._db.reference('tasks').get()
        return tasks

    def insert_car_ad(self, new_ad: CarDetails):
        ad_dict = new_ad.model_dump(mode='json')
        self._db.reference(self.path).child(new_ad.id).set(ad_dict)
        self._logger.info(f"{new_ad.id} is created successfully, "
                    f"{new_ad.manuf_en} "
                    f"{new_ad.car_model}, "
                    f"current_price: {new_ad.price}, "
                    f"{new_ad.kilometers} [km], "
                    f"year: {new_ad.year}, "
                    f"hand: {new_ad.hand}")



    def update_car_ad(self, new_ad: CarDetails, data: dict) -> Optional[CarDetails]:
        try:
            ad: dict = data[new_ad.id]
        except Exception as e:
            self._logger.error(f"Error updating car ad: {e}")
            return None

        db_ad: CarDetails = CarDetails(**ad)
        if new_ad.prices and db_ad.prices[-1].price != new_ad.prices[-1].price:
            db_ad.prices.append(new_ad.prices[-1])
            db_ad.price = new_ad.price
            self._logger.info(f"{new_ad.id} is changed, {new_ad.manuf_en}  {new_ad.car_model}, "
                        f"current_price: {new_ad.price}, "
                        f"{new_ad.kilometers} [km], year: {new_ad.year}, hand: {new_ad.hand}")
            self._logger.info(f"price changed: {db_ad.prices[-2].price} ===> {db_ad.prices[-1].price}")
            self._db.reference(self.path).child(new_ad.id).update(db_ad.model_dump(mode='json'))
        return db_ad


    def collection_exists(self):
        return self._db.reference(self.path).get() is not None

    def create_collection(self, results: List[CarDetails]):
        try:
            data: dict = {ad.id: ad.model_dump(mode='json') for ad in results}
            self._db.reference(self.path).set(data)
        except Exception as e:
            self._logger.error(f"Error adding new cars to db: {e}")

    def handle_results(self, results: List[CarDetails], user_path: str, notifier: Notifier):
        path = f'{self.ref_path}/{user_path}'
        data: dict = self._db.reference(path).get() # results already in db
        self._logger.info("Handling results")
        try:
            for ad in results:
                if ad.id not in data:
                    self.insert_car_ad(ad)
                    notifier.new_car_ad(ad)
                else:
                    old_ad: Optional[CarDetails] = self.update_car_ad(ad, data)
                    if old_ad:
                        notifier.updated_car_ad(ad, old_ad)
        except Exception as e:
            self._logger.error(f"Error updating database: {e}")

        db_data_dict = {}
        try:
            db_data_dict = {ad: CarDetails(**data[ad]) for ad in data}
        except Exception as e:
            self._logger.error(f"Error creating CarDetails: {e}")
            return
        self._logger.info("Handling sold items")
        new_ads: Dict[str, CarDetails] = {ad.id: ad for ad in results}
        self.handle_removed_ads(new_ads, db_data_dict, notifier)

    def handle_removed_ads(self, new_ads: Dict[str, CarDetails],
                           ads_db: Dict[str, CarDetails],
                           notifier: Notifier):
        for id_, ad_db in ads_db.items():
            if id_ not in new_ads:
                self._logger.info(f"removed ad: {json.dumps(ad_db.model_dump(mode='json'), ensure_ascii=False)}")
                message = html_criteria_mail(ad_db)
                notifier.removed_car_ad(ad_db)
                # self.mail_sender.send(message,
                #                        f'💸 {ad_db.manufacturer_he} {ad_db.car_model} {ad_db.city}')
                self._db.reference(self.sold_path).child(ad_db.id).set(ad_db.model_dump(mode='json'))
                self._logger.info(f"removing item {ad_db.id} from main db")
                self._db.reference(self.path).child(ad_db.id).delete()

    def clear_all_tasks(self):
        tasks_ref = self._db.reference('tasks')
        tasks = tasks_ref.get()
        if tasks:
            print("Clearing all tasks. Task info:")
            for task_id, task_dict in tasks.items():
                print(f"Task ID: {task_id}", task_dict)
            tasks_ref.delete()
            self._logger.info(f"All tasks have been removed by debug clear_all_tasks(). {len(tasks)} tasks deleted.")
            return list(tasks.values())
        else:
            print("No tasks to clear.")
            return []

