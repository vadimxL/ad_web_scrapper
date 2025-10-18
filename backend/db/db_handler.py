import json
from logging import Logger
from typing import Dict, List, Optional

from backend import models
from backend.car_details import CarDetails
from backend.db.database import Database
from backend.notifier import Notifier


class DbHandler:
    ref_path = "cars"
    ref_path_sold = "sold_cars"

    def __init__(self, db: Database, logger: Logger):
        self._db: Database = db
        self._logger = logger

    def insert_task(self, task: models.Task) -> None:
        task_dict = task.model_dump(mode='json')
        self._db.reference('tasks').child(task.id).set(task_dict)
        self._logger.info(f"Task {task.id} is created successfully, {task}")

    def get_task(self, task_id: str) -> Optional[models.Task]:
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
        return self._db.reference('tasks').child(task_id).delete()

    def load_tasks(self) -> Optional[Dict]:
        tasks = self._db.reference('tasks').get()
        return tasks

    def _insert_car_ad(self, path: str, new_ad: CarDetails):
        ad_dict = new_ad.model_dump(mode='json')
        self._db.reference(f"{self.ref_path}/{path}").child(new_ad.id).set(ad_dict)
        self._logger.info(f"{new_ad.id} is created successfully, "
                    f"{new_ad.manuf_en} "
                    f"{new_ad.car_model}, "
                    f"current_price: {new_ad.price}, "
                    f"{new_ad.kilometers} [km], "
                    f"year: {new_ad.year}, "
                    f"hand: {new_ad.hand}")


    def update_car_ad(self, path: str, new_ad: CarDetails, car_ads_from_db: Dict[str, CarDetails]) -> bool:
        db_ad: CarDetails = car_ads_from_db.get(new_ad.id)
        if db_ad is None:
            self._logger.error(f"Old ad not found in DB for ID: {new_ad.id}")
            return False
        if new_ad.prices and db_ad.prices[-1].price != new_ad.prices[-1].price:
            db_ad.prices.append(new_ad.prices[-1])
            db_ad.price = new_ad.price
            self._logger.info(f"{new_ad.id} is changed, {new_ad.manuf_en}  {new_ad.car_model}, "
                        f"current_price: {new_ad.price}, "
                        f"{new_ad.kilometers} [km], year: {new_ad.year}, hand: {new_ad.hand}")
            self._logger.info(f"price changed: {db_ad.prices[-2].price} ===> {db_ad.prices[-1].price}")
            self._db.reference(f"{self.ref_path}/{path}").child(new_ad.id).update(db_ad.model_dump(mode='json'))
            return True
        return False

    def collection_exists(self, path: str) -> bool:
        return self._db.reference(f"{self.ref_path}/{path}").get() is not None

    def create_collection(self, path: str, results: List[CarDetails]):
        try:
            data: dict = {ad.id: ad.model_dump(mode='json') for ad in results}
            self._logger.info(f"Creating new collection at {self.ref_path}/{path} with {len(data)} items")
            self._db.reference(f"{self.ref_path}/{path}").set(data)
        except Exception as e:
            self._logger.error(f"Error adding new cars to db: {e}")

    def _get_car_ads_from_db(self, path: str) -> Dict[str, CarDetails]:
        path = f'{self.ref_path}/{path}'
        car_ads_from_db: dict = self._db.reference(path).get()
        db_data_dict = {}
        try:
            db_data_dict = {id: CarDetails(**car_ads_from_db[id]) for id in car_ads_from_db}
        except Exception as e:
            self._logger.error(f"Error creating CarDetails: {e}")
            return db_data_dict
        return db_data_dict

    def handle_results(self, ads: List[CarDetails], path: str, notifier: Notifier):
        car_ads_from_db: Dict[str, CarDetails] = self._get_car_ads_from_db(path)
        if not car_ads_from_db:
            self._logger.info(f"No ads in db for {path=}")
            return

        self._logger.info(f"Handling scraped {len(ads)=}")
        try:
            for ad in ads:
                if ad.id not in car_ads_from_db: # new ad
                    self._insert_car_ad(path, ad)
                    notifier.new_car_ad(ad)
                elif self.update_car_ad(path, ad, car_ads_from_db): # updated ad
                    notifier.updated_car_ad(ad)
                else:
                    self._logger.info(f"No changes for {ad=}")

        except Exception as e:
            self._logger.error(f"Error updating database: {e}")

        db_data_dict = {}
        try:
            db_data_dict = {ad: CarDetails(**car_ads_from_db[ad]) for ad in car_ads_from_db}
        except Exception as e:
            self._logger.error(f"Error creating CarDetails: {e}")
            return
        self._logger.info("Handling sold items")
        new_ads: Dict[str, CarDetails] = {ad.id: ad for ad in ads}
        self.handle_removed_ads(path, new_ads, db_data_dict, notifier)

    def handle_removed_ads(self,
                           path: str,
                           new_ads: Dict[str, CarDetails],
                           ads_db: Dict[str, CarDetails],
                           notifier: Notifier,
                           ):
        for id_, ad_db in ads_db.items():
            if id_ not in new_ads:
                self._logger.info(f"removed ad: {json.dumps(ad_db.model_dump(mode='json'), ensure_ascii=False)}")
                notifier.removed_car_ad(ad_db)
                self._add_ad_to_sold(ad_db, path)
                self._logger.info(f"removing item {ad_db.id} from main db")
                self._db.reference(f"{self.ref_path}/{path}").child(ad_db.id).delete()

    def _add_ad_to_sold(self, ad: CarDetails, path: str):
        self._db.reference(f"{self.ref_path_sold}/{path}").child(ad.id).set(ad.model_dump(mode='json'))
        self._logger.info(f"Ad {ad.id} added to sold cars.")

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

