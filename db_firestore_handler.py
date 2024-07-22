import os
from dotenv import load_dotenv
import deepdiff
from typing import List, Dict, Callable
from firebase_admin import firestore
from google.cloud.firestore_v1 import DocumentReference, CollectionReference

import models
from loguru import logger

load_dotenv()
if "ADS_DB_PATH" not in os.environ:
    raise Exception("ADS_DB_PATH not found in environment variables")
if "ADS_ARCHIVE_DB_PATH" not in os.environ:
    raise Exception("ADS_ARCHIVE_DB_PATH not found in environment variables")

ADS_DB_PATH: str = os.environ.get("ADS_DB_PATH")
ADS_ARCHIVE_DB_PATH: str = os.environ.get("ADS_ARCHIVE_DB_PATH")

class FbDbHandler:
    ref_path = ADS_DB_PATH
    ref_path_archive = ADS_ARCHIVE_DB_PATH

    def __init__(self,
                 on_new_cb: Callable[[models.AdDetails], None],
                 on_update_cb: Callable[[models.AdDetails], None],
                 on_archive_cb: Callable[[List[models.AdDetails]], None],
                 user_path: str = None):
        if not user_path:
            self.path = self.ref_path
            self.sold_path = self.ref_path_archive
        else:
            self.path = f'{self.ref_path}/{user_path}'
            self.sold_path = f'{self.ref_path_archive}/{user_path}'
        self.on_update_cb = on_update_cb
        self.on_new_cb = on_new_cb
        self.on_archive_cb = on_archive_cb
        self.db = firestore.client()

    @classmethod
    def insert_task(cls, task: models.Task):
        task_dict = task.model_dump(mode='json')

        firestore.client().collection('tasks').document(task.id).set(task_dict)
        logger.info(f"Task {task.id} is created successfully, {task}")

    @classmethod
    def get_task(cls, task_id: str) -> models.Task:
        task_dict: Dict = firestore.client().collection('tasks').document(task_id).get()
        if task_dict is None:
            return None
        task = models.create_task_from_dict(task_dict)
        return task

    @classmethod
    def get_tasks(cls) -> List[models.Task]:
        tasks_list = []
        tasks = firestore.client().collection('tasks').stream()
        for task_dict in tasks:
            tasks_list.append(models.create_task_from_dict(task_dict))
        return tasks_list

    @classmethod
    def create_listener(cls, callback):
        db = firestore.client()
        ref = db.collection('tasks')
        ref.on_snapshot(callback)

    @classmethod
    def update_task(cls, task: models.Task):
        task_dict = task.model_dump(mode='json')
        cls.db.colletion('tasks').document(task.id).update(task_dict)
        logger.info(f"Task {task.id} is updated successfully, {task}")

    @classmethod
    def delete_task(cls, task_id: str) -> models.Task:
        cls.db.colletion('tasks').document(task_id).delete()

    @classmethod
    def load_tasks(cls) -> Dict:
        return cls.db.colletion('tasks').get()

    def insert_ad(self, ad: models.AdDetails):
        self.db.colletion(self.path).document(ad.id).set(ad.model_dump(mode='json'))
        logger.info(f"{ad.id} is created successfully, "
                    f"{ad.manuf_en} "
                    f"{ad.car_model}, "
                    f"current_price: {ad.price}, "
                    f"{ad.kilometers} [km], "
                    f"year: {ad.year}, "
                    f"hand: {ad.hand}")

    def get_archive(self):
        ads: dict = self.db.colletion(self.sold_path).get()
        archive = []
        for id_, ad in ads.items():
            archive.append(models.AdDetails(**ad))
        return archive

    def update_ad(self, new_ad: models.AdDetails, db_ad: models.AdDetails) -> bool:
        try:
            d1 = new_ad.model_dump(mode='json')
            self.db.colletion("/test").document(d1["id"]).set(d1)
            d1 = self.db.colletion("/test").document(d1["id"]).get()
            d2 = self.db_ad.model_dump(mode='json')
            ddiff = deepdiff.DeepDiff(d1, d2, ignore_order=True, include_paths="root['full_info']")
            jsonized_diff = ddiff.to_json(ensure_ascii=False)
            if jsonized_diff:
                logger.info(f"ad: {new_ad.id} is updated, deepdiff: {jsonized_diff}")

            if new_ad.prices and self.db_ad.prices[-1].price != new_ad.prices[-1].price:
                db_ad.prices.append(new_ad.prices[-1])
                logger.info(f"{new_ad.id} price is changed {db_ad.prices[-2].price} ==> {db_ad.prices[-1].price} "
                            f"{new_ad.manuf_en}  {new_ad.car_model} {new_ad.price} "
                            f"{new_ad.kilometers} [km], year: {new_ad.year}, hand: {new_ad.hand}")

            new_ad.prices = db_ad.prices
            self.db.colletion(self.path).document(new_ad.id).update(new_ad.model_dump(mode='json'))
            return False
        except Exception as e:
            logger.error(f"Error updating car ad: {e}")
            return False

    def collection_exists(self):
        return self.db.colletion(self.path).get() is not None

    def create_collection(self, results: List[models.AdDetails]):
        try:
            data: dict = {ad.id: ad.model_dump(mode='json') for ad in results}
            self.db.colletion(self.path).set(data)
        except Exception as e:
            logger.error(f"Error adding new cars to db: {e}")

    def handle_results(self, results: List[models.AdDetails], task: models.Task):
        data: dict = self.db.colletion(self.path).get()  # results already in db
        logger.info(f"Handling results")
        try:
            for ad in results:
                if ad.id not in data:
                    self.insert_ad(ad)
                    self.on_new_cb(ad)
                else:
                    if self.update_ad(ad, models.AdDetails(**data[ad.id])):
                        self.on_update_cb(ad)
        except Exception as e:
            logger.error(f"Error updating database: {e}")

        db_data_dict = {}
        try:
            db_data_dict: dict = {ad: models.AdDetails(**data[ad]) for ad in data}
        except Exception as e:
            logger.error(f"Error creating AdDetails: {e}")
            return
        logger.info(f"Handling archived items")
        # filter db_data_dict to only include items that are in results
        manufacturers = task.manufacturers
        for ad in list(db_data_dict.keys()):
            if db_data_dict[ad].manufacturer_he not in manufacturers:
                del db_data_dict[ad]

        if "model" in task.params:
            for ad in list(db_data_dict.keys()):
                if str(db_data_dict[ad].full_info['ModelID']) not in task.params['model']:
                    del db_data_dict[ad]

        archived = self.archive({ad.id: ad for ad in results}, db_data_dict)
        self.on_archive_cb(archived)

    def archive(self, new_ads: Dict[str, models.AdDetails], ads_db: Dict[str, models.AdDetails]) -> List[
        models.AdDetails]:
        archived = []
        for id_, ad_db in ads_db.items():
            if id_ not in new_ads:
                archived.append(ad_db)
                self.db.colletion(self.sold_path).document(ad_db.id).set(ad_db.model_dump(mode='json'))
                logger.info(f"archiving ad {ad_db.id} from main db, probably sold")
                self.db.colletion(self.path).document(ad_db.id).delete()
        return archived
