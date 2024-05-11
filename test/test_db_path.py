import json
import unittest

import firebase_db
from scraper import urls, Scraper
from firebase_admin import db
from firebase_admin.db import Reference

class TestScraper(unittest.TestCase):
    def test_db_path(self):
        for url in urls:
            db_path = Scraper.db_path(url)
            print(db_path)
        self.assertEqual(True, False)  # add assertion here

    def test_print_order_by_price(self):
        firebase_db.init_firebase_db()
        ref = db.reference('car_ads_test')
        snapshot = ref.order_by_child('price').get()
        for key, val in snapshot.items():
            print('{0} was {1} meters tall'.format(key, val))
    def test_print_from_year(self):
        firebase_db.init_firebase_db()
        ref = db.reference('car_ads_test')
        snapshot = ref.order_by_child('year').equal_to(2022).get()
        for key in snapshot:
            print(key)

    def test_add_new_car(self):
        firebase_db.init_firebase_db()
        db_ref = db.reference(f'/car_ads_test')
        with open("car_ads_sample.json", "r") as f:
            cars_ads_list = json.loads(f.read())[0]
            cars_ads_dict = {car_ad['id']: car_ad for car_ad in cars_ads_list}
            print(cars_ads_dict)
            db_ref.set(cars_ads_dict)
            # for car in cars_ads_list:
            #     child = db_ref.child(f"{car['manuf_en']}/year_{car['year']}/hand_{car['hand']}/{car['id']}")
            #     res = child.update(car)
            #     print(res)


if __name__ == '__main__':
    unittest.main()
