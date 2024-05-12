import logging
from dataclasses import asdict
from typing import List

import jinja2
from firebase_admin import db
from firebase_admin.db import Reference
import firebase_db
from car_details import CarDetails
from gmail_sender.gmail_sender import GmailSender

logger = logging.getLogger("ad_web_scrapper")


class DbHandler:
    ref_path = "cars"
    ref_path_sold = "sold_cars"

    def __init__(self, user_path: str):
        self.user_path = user_path
        self.path = f'{self.ref_path}/{self.user_path}'
        self.gmail_sender = GmailSender()

    def insert_car_ad(self, new_ad: CarDetails):
        db.reference(self.path).child(new_ad.id).set(asdict(new_ad))
        logger.info(f"{new_ad.id} is created successfully, "
                    f"{new_ad.manuf_en} "
                    f"{new_ad.car_model}, "
                    f"current_price: {new_ad.price}, "
                    f"{new_ad.kilometers} [km], "
                    f"year: {new_ad.year}, "
                    f"hand: {new_ad.hand}")

        try:
            message = self.html_criteria_mail(new_ad)
            self.gmail_sender.send(message,
                                   f'🎁 [New] - {new_ad.manufacturer_he} {new_ad.car_model} {new_ad.city}')
        except Exception as e:
            logger.error(f"Error sending email: {e}")

    def update_car_ad(self, new_ad: CarDetails):
        try:
            ad: dict = db.reference(self.path).child(new_ad.id).get()
        except Exception as e:
            logger.error(f"Error updating car ad: {e}")
            return

        db_ad: CarDetails = CarDetails(**ad)
        if new_ad.prices and db_ad.prices[-1].price != new_ad.prices[-1].price:
            db_ad.prices.append(new_ad.prices[-1])
            logger.info(f"{new_ad.id} is changed, {new_ad.manuf_en}  {new_ad.car_model}, "
                        f"current_price: {new_ad.price}, "
                        f"{new_ad.kilometers} [km], year: {new_ad.year}, hand: {new_ad.hand}")
            logger.info(f"price changed: {db_ad.prices[-2].price} ===> {db_ad.prices[-1].price}")

            try:
                message = self.html_criteria_mail(new_ad)
                self.gmail_sender.send(message,
                                       f'⬇️ [Update] - {new_ad.manufacturer_he} {new_ad.car_model} {new_ad.car_model} {new_ad.city}')
            except Exception as e:
                logger.error(f"Error sending email: {e}")

    def html_criteria_mail(self, car_details: CarDetails):
        environment = jinja2.Environment()
        with open("criteria_mail.html") as file:
            template = environment.from_string(file.read())
            return template.render(id=car_details.id,
                                   manufacturer=car_details.manuf_en,
                                   hand=car_details.hand,
                                   model=car_details.car_model,
                                   year=car_details.year,
                                   km=car_details.kilometers,
                                   price=car_details.price,
                                   free_text="",
                                   initial_price=car_details.prices[0].price,
                                   date_created=car_details.date_added)

    def create_collection(self, results: List[CarDetails]):
        try:
            db.reference(self.path).set({ad.id: asdict(ad) for ad in results})
        except ValueError as e:
            logger.error(f"Error adding new cars to db: {e}")
        except Exception as e:
            logger.error(f"Error adding new cars to db: {e}")

    def handle_results(self, results: List[CarDetails]):
        data = db.reference(self.path).get(shallow=True)
        try:
            for ad in results:
                if ad.id not in data:
                    self.insert_car_ad(ad)
                else:
                    self.update_car_ad(ad)
        except Exception as e:
            logger.error(f"Error updating database: {e}")

            # self.handle_sold_items([asdict(new_ad) for new_ad in new_ads], db_path, ref)

    def handle_sold_items(self, scraped_car_ads: list[dict], db_path: str, ref: Reference):
        sold_items = []
        car_ads_db = ref.get(shallow=True)
        car_ads: dict = {d['id']: d for d in scraped_car_ads}
        if car_ads_db:
            for key, value in car_ads_db.items():
                if key not in car_ads:
                    car_ad_db: dict = ref.child(key).get()
                    sold_car = {"id": car_ad_db['id'],
                                'manufacturer': car_ad_db['manuf_en'], 'model': car_ad_db['car_model'],
                                'date_added': car_ad_db['date_added'], 'current_price': car_ad_db['current_price'],
                                'price_history': car_ad_db['prices'], 'km': car_ad_db['kilometers'],
                                'year': car_ad_db['year'], 'hand': car_ad_db['hand']}
                    logger.info(f"sold car: {json.dumps(sold_car, ensure_ascii=False)}")
                    message = self.html_criteria_mail(car_ad_db)
                    self.gmail_sender.send(message,
                                           f'💸 [Sold] - {car_ad_db["manufacturer_he"]} {car_ad_db["car_model"]} {car_ad_db["city"]}')
                    sold_items.append(car_ad_db)

            # add sold cars to a separate list
            db_path_for_sold = f'/sold_cars{db_path}'

            if sold_items:
                try:
                    db.reference(db_path_for_sold).update({car_ad['id']: car_ad for car_ad in sold_items})
                except ValueError as e:
                    logger.error(f"Error adding sold cars to db: {e}")

            # remove from main db, for next time
            for item in sold_items:
                logger.info(f"removing item {item['id']} from main db")
                db.reference(db_path).child(item['id']).delete()
        return car_ads_db
