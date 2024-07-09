import json
import unittest
from datetime import datetime

import firebase_db
from car_details import AdDetails, PriceHistory
from db_handler import DbHandler
from gmail_sender.gmail_sender import GmailSender


class TestDbHandler(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, False)  # add assertion here

    def test_handle_results(self):
        user_path = "manufacturer=21&model=578&year=2020-2024&price=-1-150000&km=-1-100000"
        firebase_db.init_firebase_db()
        with open("cars_sample.json", "r") as f:
            car_ads = json.loads(f.read())["cars"][user_path]
            ads = []
            for ad in car_ads.values():
                try:
                    d = datetime.strptime(ad['prices'][-1]['date'], '%d/%m/%Y')
                except Exception as e:
                    print(f"Error parsing date: {e}")
                # price_hist = PriceHistory(price=ad['price'], date=d)
                try:
                    ad['prices'][-1]['date'] = d
                    car_details = AdDetails(**ad)
                except Exception as e:
                    print(f"Error creating AdDetails: {e}")
                    return
                # car_details.prices = [price_hist]
                ads.append(car_details)
            gmail_sender = GmailSender("../gmail_sender/credentials.json")
            db_handler = DbHandler(gmail_sender, "test")
            # db_handler.create_collection(ads)
            db_handler.handle_results(ads)


if __name__ == '__main__':
    unittest.main()
