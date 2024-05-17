import json
import logging
from dataclasses import asdict
from typing import List, Dict
import jinja2
from firebase_admin import db
from firebase_admin.db import Reference
from car_details import CarDetails
from gmail_sender.gmail_sender import GmailSender

logger = logging.getLogger("ad_web_scrapper")

criteria_mail = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Title</title>
</head>
<body>
<table align="center" border="0" cellpadding="0" cellspacing="0" width="100%"
       style="border-collapse:collapse;max-width:600px!important">
    <tbody>
    <tr>
        <td valign="top"
            style="background:transparent none no-repeat center/cover;border-top:0;border-bottom:0;padding-top:0;padding-bottom:0">
            <table border="0" cellpadding="0" cellspacing="0" width="100%"
                   style="min-width:100%;border-collapse:collapse">
                <tbody>
                <tr>
                    <td valign="top" style="padding-top:9px">
                        <table style="max-width:100%;min-width:100%;border-collapse:collapse">
                            <tbody>
                            <tr>
                                <td valign="top"
                                    style="padding:0 18px 9px;word-break:break-word;color:#808080;font-family:Helvetica,serif;font-size:16px;line-height:150%">
                                    <h3 style="display:block;margin:0;padding:0;color:#444444;font-family:Helvetica,serif;font-size:22px;font-style:normal;font-weight:bold;line-height:150%;letter-spacing:normal">
                                        <span style="font-family:arial,helvetica neue,helvetica,sans-serif">{{manufacturer}}</span>
                                    </h3>
                                    <ul>
                                        <li>
                                            <span style="font-family:arial,helvetica neue,helvetica,sans-serif">id: {{id}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">date created: {{date_created}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">hand: {{hand}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">year: {{year}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">gear: {{gear_type}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">model: {{model}}</span>
                                        </li>
                                        <li><span
                                                style="font-family:arial,helvetica neue,helvetica,sans-serif">mileage: {{km}} [km]</span>
                                        </li>
                                        <ul>
                                            {% for item in free_text.split('\n') %}
                                            <li><span
                                                    style="font-family:arial,helvetica neue,helvetica,sans-serif">{{item}}</span>
                                            </li>
                                            {% endfor %}
                                        </ul>
                                    </ul>
                                    <div>
                                        <span style="font-family:arial,helvetica neue,helvetica,sans-serif">
                                           <span style="font-family:arial,helvetica neue,helvetica,sans-serif">
                                               <strong>price: {{price}}&nbsp;</strong>
                                               <span style="font-size:14px">initial price: {{initial_price}}</span>
                                           </span>
                                       </span>
                                    </div>
                                </td>
                            </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
                </tbody>
            </table>
            <table border="0" cellpadding="0" cellspacing="0" width="100%"
                   style="min-width:100%;border-collapse:collapse">
                <tbody>
                <tr>
                    <td style="padding: 0 18px 18px;" valign="top"
                        align="center">
                        <table border="0" cellpadding="0" cellspacing="0"
                               style="border-collapse:separate!important;border-radius:3px;background-color:#00add8">
                            <tbody>
                            <tr>
                                <td align="center" valign="middle"
                                    style="font-family:Helvetica,serif;font-size:18px;padding:18px">
                                    <a title="צפיה בפרטים המלאים"
                                       href="https://www.yad2.co.il/vehicles/item/{{id}}"
                                       style="font-weight:bold;letter-spacing:-0.5px;line-height:100%;text-align:center;text-decoration:none;color:#ffffff;display:block"
                                       target="_blank"
                                       >צפיה בפרטים המלאים</a>
                                </td>
                            </tr>
                            </tbody>
                        </table>
                    </td>
                </tr>
                </tbody>
            </table>
        </td>
    </tr>
    </tbody>
</table>
</body>
</html>"""


class DbHandler:
    ref_path = "cars"
    ref_path_sold = "sold_cars"

    def __init__(self, user_path: str, mail_sender: GmailSender):
        self.user_path = user_path
        self.path = f'{self.ref_path}/{self.user_path}'
        self.sold_path = f'{self.ref_path_sold}/{self.user_path}'
        self.gmail_sender = mail_sender

    def insert_car_ad(self, new_ad: CarDetails):
        ad_dict = new_ad.model_dump(mode='json')
        db.reference(self.path).child(new_ad.id).set(ad_dict)
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

    def update_car_ad(self, new_ad: CarDetails, data: dict):
        try:
            ad: dict = data[new_ad.id]
        except Exception as e:
            logger.error(f"Error updating car ad: {e}")
            return

        db_ad: CarDetails = CarDetails(**ad)
        if new_ad.prices and db_ad.prices[-1].price != new_ad.prices[-1].price:
            db_ad.prices.append(new_ad.prices[-1])
            db_ad.price = new_ad.price
            logger.info(f"{new_ad.id} is changed, {new_ad.manuf_en}  {new_ad.car_model}, "
                        f"current_price: {new_ad.price}, "
                        f"{new_ad.kilometers} [km], year: {new_ad.year}, hand: {new_ad.hand}")
            logger.info(f"price changed: {db_ad.prices[-2].price} ===> {db_ad.prices[-1].price}")
            db.reference(self.path).child(new_ad.id).update(db_ad.model_dump(mode='json'))

            try:
                message = self.html_criteria_mail(db_ad)
                last_price = db_ad.prices[-1].price
                previous_price = db_ad.prices[-2].price
                if last_price < previous_price:
                    subject = f'⬇️ [Update] - {new_ad.manufacturer_he} {new_ad.car_model} {new_ad.city}'
                else:
                    subject = f'⬆️ [Update] - {new_ad.manufacturer_he} {new_ad.car_model} {new_ad.city}'

                self.gmail_sender.send(message, subject)
            except Exception as e:
                logger.error(f"Error sending email: {e}")

    def html_criteria_mail(self, car_details: CarDetails):
        environment = jinja2.Environment()
        template = environment.from_string(criteria_mail)

        # Transforming the list to a single human-readable string
        human_readable_str = ""
        for history in car_details.prices:
            date_str = history.date.strftime("%B %d, %Y")
            human_readable_str += f"On {date_str}, the price was {history.price} NIS.\n"

        return template.render(id=car_details.id,
                               manufacturer=car_details.manuf_en,
                               hand=car_details.hand,
                               model=car_details.car_model,
                               year=car_details.year,
                               km=car_details.kilometers,
                               price=car_details.price,
                               gear_type=car_details.gear_type,
                               free_text=human_readable_str.strip(),
                               initial_price=car_details.prices[0].price,
                               date_created=car_details.date_added)

    def create_collection(self, results: List[CarDetails]):
        try:
            data: dict = {ad.id: ad.model_dump(mode='json') for ad in results}
            db.reference(self.path).set(data)
        except Exception as e:
            logger.error(f"Error adding new cars to db: {e}")

    def handle_results(self, results: List[CarDetails]):
        data: dict = db.reference(self.path).get()
        try:
            for ad in results:
                if ad.id not in data:
                    self.insert_car_ad(ad)
                else:
                    self.update_car_ad(ad, data)
        except Exception as e:
            logger.error(f"Error updating database: {e}")

        db_data_dict = {}
        try:
            db_data_dict = {ad: CarDetails(**data[ad]) for ad in data}
        except Exception as e:
            logger.error(f"Error creating CarDetails: {e}")
            return

        self.handle_sold_items({ad.id: ad for ad in results}, db_data_dict)

    def handle_sold_items(self, new_ads: Dict[str, CarDetails], ads_db: Dict[str, CarDetails]):
        for id_, ad_db in ads_db.items():
            if id_ not in new_ads:
                logger.info(f"sold car: {json.dumps(ad_db.model_dump(mode='json'), ensure_ascii=False)}")
                message = self.html_criteria_mail(ad_db)
                self.gmail_sender.send(message,
                                       f'💸 [Sold] - {ad_db.manufacturer_he} {ad_db.car_model} {ad_db.city}')
                db.reference(self.sold_path).child(ad_db.id).set(ad_db.model_dump(mode='json'))
                logger.info(f"removing item {ad_db.id} from main db")
                db.reference(self.path).child(ad_db.id).delete()


