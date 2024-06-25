from datetime import datetime

import json
import logging
from typing import List, Dict
from firebase_admin import db
import models
from car_details import CarDetails
from criteria_model import html_criteria_mail
from email_sender.email_sender import EmailSender
from logger_setup import ads_updates_logger, internal_info_logger


class DbHandler:
    ref_path = "cars"
    ref_path_sold = "sold_cars"

    def __init__(self, user_path: str, mail_sender: EmailSender):
        self.user_path = user_path
        self.path = f'{self.ref_path}/{self.user_path}'
        self.sold_path = f'{self.ref_path_sold}/{self.user_path}'
        self.gmail_sender = mail_sender

    @classmethod
    def insert_task(cls, task: models.Task):
        task_dict = task.model_dump(mode='json')
        db.reference('tasks').child(task.id).set(task_dict)
        internal_info_logger.info(f"Task {task.id} is created successfully, {task}")

    @classmethod
    def get_task(cls, task_id: str) -> models.Task:
        task_dict: Dict = db.reference('tasks').child(task_id).get()
        if task_dict is None:
            return None
        task = models.create_task_from_dict(task_dict)
        return task

    @classmethod
    def create_listener(cls, callback):
        ref = db.reference('tasks')
        ref.listen(callback)

    @classmethod
    def update_task(cls, task: models.Task):
        task_dict = task.model_dump(mode='json')
        db.reference('tasks').child(task.id).update(task_dict)
        internal_info_logger.info(f"Task {task.id} is updated successfully, {task}")

    @classmethod
    def delete_task(cls, task_id: str) -> models.Task:
        task_dict = db.reference('tasks').child(task_id).delete()
        internal_info_logger.info(f"Task {task_id} is deleted successfully")
        task = models.create_task_from_dict(task_dict)
        return task

    @classmethod
    def load_tasks(cls) -> Dict:
        tasks: Dict = db.reference('tasks').get()
        return tasks

    def insert_car_ad(self, new_ad: CarDetails):
        ad_dict = new_ad.model_dump(mode='json')
        db.reference(self.path).child(new_ad.id).set(ad_dict)
        internal_info_logger.info(f"{new_ad.id} is created successfully, "
                    f"{new_ad.manuf_en} "
                    f"{new_ad.car_model}, "
                    f"current_price: {new_ad.price}, "
                    f"{new_ad.kilometers} [km], "
                    f"year: {new_ad.year}, "
                    f"hand: {new_ad.hand}")

        try:
            message = html_criteria_mail(new_ad)
            self.gmail_sender.send(message,

                                   f'🎁 [New] - {new_ad.manufacturer_he} {new_ad.car_model} {new_ad.city}')
        except Exception as e:
            internal_info_logger.error(f"Error sending email: {e}")

    def update_car_ad(self, new_ad: CarDetails, data: dict):
        try:
            ad: dict = data[new_ad.id]
        except Exception as e:
            internal_info_logger.error(f"Error updating car ad: {e}")
            return

        db_ad: CarDetails = CarDetails(**ad)
        if new_ad.prices and db_ad.prices[-1].price != new_ad.prices[-1].price:
            db_ad.prices.append(new_ad.prices[-1])
            db_ad.price = new_ad.price
            ads_updates_logger.info(f"{new_ad.id} is changed, {new_ad.manuf_en}  {new_ad.car_model}, "
                        f"current_price: {new_ad.price}, "
                        f"{new_ad.kilometers} [km], year: {new_ad.year}, hand: {new_ad.hand}")
            ads_updates_logger.info(f"price changed: {db_ad.prices[-2].price} ===> {db_ad.prices[-1].price}")
            db.reference(self.path).child(new_ad.id).update(db_ad.model_dump(mode='json'))

            try:
                message = html_criteria_mail(db_ad)
                last_price = db_ad.prices[-1].price
                previous_price = db_ad.prices[-2].price
                if last_price < previous_price:
                    subject = f'⬇️ [Update] - {new_ad.manufacturer_he} {new_ad.car_model} {new_ad.city}'
                else:
                    subject = f'⬆️ [Update] - {new_ad.manufacturer_he} {new_ad.car_model} {new_ad.city}'

                self.gmail_sender.send(message, subject)
            except Exception as e:
                internal_info_logger.error(f"Error sending email: {e}")
        else: # Nothing changed
            ads_updates_logger.info(f"{new_ad.id} is unchanged, {new_ad.manuf_en}  {new_ad.car_model}, "
                        f"current_price: {new_ad.price}, "
                        f"{new_ad.kilometers} [km], year: {new_ad.year}, hand: {new_ad.hand}")


    def collection_exists(self):
        return db.reference(self.path).get() is not None

    def create_collection(self, results: List[CarDetails]):
        try:
            data: dict = {ad.id: ad.model_dump(mode='json') for ad in results}
            db.reference(self.path).set(data)
        except Exception as e:
            internal_info_logger.error(f"Error adding new cars to db: {e}")

    def handle_results(self, results: List[CarDetails]):
        data: dict = db.reference(self.path).get()
        try:
            for ad in results:
                if ad.id not in data:
                    self.insert_car_ad(ad)
                else:
                    self.update_car_ad(ad, data)
        except Exception as e:
            internal_info_logger.error(f"Error updating database: {e}")

        db_data_dict = {}
        try:
            db_data_dict = {ad: CarDetails(**data[ad]) for ad in data}
        except Exception as e:
            internal_info_logger.error(f"Error creating CarDetails: {e}")
            return

        self.handle_sold_items({ad.id: ad for ad in results}, db_data_dict)

    def handle_sold_items(self, new_ads: Dict[str, CarDetails], ads_db: Dict[str, CarDetails]):
        for id_, ad_db in ads_db.items():
            if id_ not in new_ads:
                ads_updates_logger.info(f"sold car: {json.dumps(ad_db.model_dump(mode='json'), ensure_ascii=False)}")
                message = html_criteria_mail(ad_db)
                self.gmail_sender.send(message,
                                       f'💸 [Sold] - {ad_db.manufacturer_he} {ad_db.car_model} {ad_db.city}')
                db.reference(self.sold_path).child(ad_db.id).set(ad_db.model_dump(mode='json'))
                ads_updates_logger.info(f"removing item {ad_db.id} from main db")
                db.reference(self.path).child(ad_db.id).delete()


