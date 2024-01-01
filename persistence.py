from firebase_admin import db
import pandas as pd
import firebase_db
import json
from datetime import datetime, timedelta

from scraper import FEED_SOURCES_PRIVATE


def dump_to_json(car_ads_to_save: dict, feed_sources: list):
    # Assuming car_ads_to_save is a list of dictionaries
    manufacturers = set(ad['manuf_en'] for ad in car_ads_to_save.values())
    if len(manufacturers) == 1:
        manufacturer = manufacturers.pop()
    else:
        manufacturer = "multiple"

    # time_now = datetime.now().strftime("%Y_%m_%d_%H")
    time_now = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    filename_json = f'json/car_ads_{manufacturer}_{"_".join(feed_sources)}_' + time_now + '.json'
    with open(filename_json, 'w', encoding='utf-8') as f1:
        json.dump(car_ads_to_save, f1, indent=4, ensure_ascii=False)


def dump_to_excel(car_ads_to_save: dict, feed_sources: list):
    # Assuming car_ads_to_save is a dict of dictionaries
    manufacturers = set(ad['manuf_en'] for ad in car_ads_to_save.values())
    # manufacturers = set(ad['manuf_en'] for ad in car_ads_to_save)
    if len(manufacturers) == 1:
        manufacturer = manufacturers.pop()
    else:
        manufacturer = "multiple"

    time_now = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    df = pd.json_normalize(car_ads_to_save.values())

    def make_hyperlink(value):
        url = "https://yad2.co.il/item/{}"
        hyperlink = '=HYPERLINK("%s", "%s")' % (url.format(value), value)
        return hyperlink

    df['id'] = df['id'].apply(make_hyperlink)
    df.to_excel(f'excel/car_ads_{manufacturer}_{"_".join(feed_sources)}_' + time_now + ".xlsx")


def get_car_ads_from_db():
    firebase_db.init_firebase_db()
    return db.reference('/car_ads/').get()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    car_ads = get_car_ads_from_db()
    feed_sources = FEED_SOURCES_PRIVATE
    dump_to_json(car_ads, feed_sources)
    dump_to_excel(car_ads, feed_sources)
