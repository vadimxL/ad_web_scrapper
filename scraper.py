import asyncio
import sys
from datetime import datetime, timedelta
import re
from firebase_admin import db
import firebase_db
import json
import time
from aiohttp_client_cache import CachedSession, SQLiteBackend, CachedResponse

from rich import print

from excel.utils.utils import human_readable_date, convert_to_human_readable_date
from handz import get_pricing_from_handz

import logging

logging.getLogger(__name__).addHandler(logging.StreamHandler(stream=sys.stdout))
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='example.log',
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8')

urls = [
    "https://www.yad2.co.il/vehicles/cars?manufacturer=48&model=3866,2829,3484&year=2019--1&km=-1-80000",  # Kia Niro
    "https://www.yad2.co.il/vehicles/cars?manufacturer=27&model=2333&year=2020--1&km=-1-100000",  # Mazda CX-5
    "https://www.yad2.co.il/vehicles/cars?manufacturer=37&model=2842&year=2020--1&km=-1-100000"  # Seat Ateca
]

FEED_SOURCES_PRIVATE = ['private']
FEED_SOURCES_COMMERCIAL = ['commercial', 'xml']
FEED_SOURCES_ALL = ['xml', 'commercial', 'private']

manufacturers_dict = {
    "hyundai": "21",
    "kia": "48",
    "seat": "37",
    "mazda": "27"
}

num_to_manuf_dict = {
    "21": "hyundai",
    "48": "kia",
    "37": "seat",
    "27": "mazda"
}

secs_to_sleep = 0.5


class Scraper:
    def __init__(self, urls_: list[str]):
        self.urls = urls_
        self.expiration = timedelta(hours=2)
        self.cache_name = 'demo_cache'

    async def scrape(self, q: dict) -> CachedResponse:
        url = "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars"

        payload = ""
        headers = {
            "cookie": "__uzmc=518554024966; __uzmd=1690101328",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "mainsite_version_commit": "7c9a9c5c1fe45ec28c16bc473d25aad7141f53bd",
            "mobile-app": "false",
            "Origin": "https://www.yad2.co.il",
            "Connection": "keep-alive",
            "Referer": "https://www.yad2.co.il/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }

        async with CachedSession(cache=SQLiteBackend(self.cache_name), expire_after=self.expiration) as session:
            r = await session.get(url, data=payload, headers=headers, params=q)

        if r.from_cache:
            logger.info(f'cache created_at: {r.created_at.strftime("%H:%M")} for page: {q.get("page")}, '
                        f'query: {q}')

        return r

    async def get_first_page(self, q: dict) -> dict:
        q['page'] = str(1)
        # Use a breakpoint in the code line below to debug your script.
        tasks = []
        scrape_task = asyncio.create_task(self.scrape(q))
        tasks.append(scrape_task)

        # Wait for all tasks to complete
        response = await asyncio.gather(*tasks)

        if not response[0].from_cache:
            print(f'Not from cache, sleeping for {secs_to_sleep} second')
            time.sleep(secs_to_sleep)

        # with open('json/first_page.json', 'w', encoding='utf-8') as f1:
        #     json.dump(response.json(), f1, indent=4, ensure_ascii=False)

        json_response = await response[0].json()
        return json_response

    def get_number_of_pages(self, first_page):
        return first_page['data']['pagination']['last_page']

    def get_total_items(self, first_page):
        return first_page['data']['pagination']['total_items']

    async def yad2_scrape(self, q: dict, feed_sources, last_page: int = 1):
        filtered_feed_items = []  # type: list
        parsed_feed_items = []
        car_ads_to_save = []
        tasks = []

        for i in range(1, last_page + 1):
            q['page'] = str(i)
            task = asyncio.create_task(self.scrape(q.copy()))
            tasks.append(task)
            # result = scrape(querystring, session)

        pages = await asyncio.gather(*tasks)

        for page in pages:
            if not page.from_cache:
                print(f'Not from cache, sleeping for {secs_to_sleep} second')
                time.sleep(secs_to_sleep)

            scraped_page = await page.json()
            feed_items = scraped_page['data']['feed']['feed_items']
            for feed_item in feed_items:
                # car_details = extract_car_details(feed_item)
                car_details = dict(sorted(feed_item.items()))
                parsed_feed_items.append(car_details)

        for item in parsed_feed_items:
            # if item['type'] != 'ad':
            #     # print(f"Skipping item {car_details['type']} because it's not an ad")
            #     continue
            #
            if 'id' not in item:
                continue

            if item['feed_source'] not in feed_sources:
                # print(f"Skipping item {car_details['feed_source']} because it's not a private ad")
                continue

            filtered_feed_items.append(item)
            car_ads_to_save.append(self.extract_car_details(item))

        handz_result = get_pricing_from_handz(filtered_feed_items, "62e8c1a08efe2d1fad068684")

        for res in handz_result['data']['entities']:
            result_filter = next(filter(lambda x: x['id'] == res['id'], car_ads_to_save), None)
            if result_filter:
                result_filter['prices'] = res['prices']
                result_filter['prices'] = human_readable_date(result_filter['prices'])
                result_filter['date_created'] = convert_to_human_readable_date(res['dateCreated'])

        return car_ads_to_save, filtered_feed_items

    def extract_car_details(self, feed_item: json):
        horsepower_value = 0
        row2_without_hp = 'N/A'
        row2 = feed_item.get('row_2', 'N/A')

        # Split the text by lines and process each line
        match = re.search(r'\((.*?)\)', row2)
        if match:
            horsepower_value = match.group(1)
            horsepower_value = re.search(r'\d+', horsepower_value).group(0)
            row2_without_hp = re.sub(r'\([^)]*\)', '', row2)

        hand = feed_item.get('Hand_text', 'N/A')
        if "ראשונה" in hand:
            hand = 1
        elif "שניה" in hand:
            hand = 2
        elif "שלישית" in hand:
            hand = 3
        elif "רביעית" in hand:
            hand = 4

        # Fix the date format
        parsed_date = datetime.strptime(feed_item['date_added'], "%Y-%m-%d %H:%M:%S")

        def excel_date(date1):
            temp = datetime(1899, 12, 30)  # Note, not 31st Dec but 30th!
            delta = date1 - temp
            return float(delta.days) + (float(delta.seconds) / 86400)

        date_added_epoch = int(excel_date(parsed_date))
        formatted_date = parsed_date.strftime("%-d/%-m/%Y")

        # Get the numeric value of the price
        # Remove currency symbol and commas
        if 'לא צוין' in feed_item['price']:
            price_numeric = 0
        else:
            price_numeric = int(feed_item['price'].replace('₪', '').replace(',', '').strip())

        mileage_numeric = int(feed_item['kilometers'].replace(',', '').strip())

        blind_spot = 'N/A'
        # Search for the string in the list
        for item in feed_item['advanced_info']['items'][2]['values']:
            if "שטח" in item and "מת" in item:
                blind_spot = item

        smart_cruise_control = 'N/A'
        # Search for the string in the list
        for item in feed_item['advanced_info']['items'][2]['values']:
            if "שיוט" in item and "אדפטיבית" in item:
                smart_cruise_control = item

        car_details = {'id': feed_item['id'], 'city': feed_item.get('city', 'N/A'),
                       'manufacturer_he': feed_item.get('manufacturer', 'N/A'),
                       'car_model': f"{feed_item['model']} {row2_without_hp}", 'hp': horsepower_value,
                       'year': feed_item['year'], 'hand': hand, 'kilometers': mileage_numeric,
                       'current_price': price_numeric, 'date_added_epoch': date_added_epoch,
                       'date_added': formatted_date,
                       'blind_spot': blind_spot,
                       'smart_cruise_control': smart_cruise_control, 'feed_source': feed_item['feed_source'],
                       'updated_at': feed_item['updated_at'], 'manuf_en': feed_item.get('manufacturer_eng', 'N/A')}

        # car_details['advanced_features'] = feed_item['advanced_info']['items'][2]['values']

        return car_details

    @staticmethod
    def querystring(url: str):
        q = {}
        for param in url.split('?')[1].split('&'):
            key, value = param.split('=')
            q[key] = value
        return q

    def upsert_car_ad(self, ad_id, new_data, ref, data: dict):
        if data and data.get(ad_id):
            car_ad = data[ad_id]
            is_changed = False
            for key, value in car_ad.items():
                # print which data is changed
                if value != new_data[key]:
                    logger.info(f"Document {ad_id} has changed: {key} changed from {value} to {new_data[key]}")
                    is_changed = True
            if is_changed:
                ref.update({ad_id: new_data})
                logger.info(f"Document is changed, {ad_id} updated successfully!")
        else:
            ref.update({ad_id: new_data})
            logger.info(f"Document {ad_id} created successfully!")

    async def get_model(self, manufacturer_id: str):
        # session = CachedSession('yad2_model_cache', backend='sqlite', expire_after=timedelta(hours=48))
        url = f"https://gw.yad2.co.il/search-options/vehicles/cars?fields=model&manufacturer={manufacturer_id}"

        print(url)

        payload = {}
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Cookie': 'leadSaleRentFree=67; y2018-2-cohort=23; __uzma=3c4eec9f-8a37-4503-a6c9-191eba2c7735; '
                      '__uzmb=1691219274; __uzmc=299333711915; __uzmd=1704738443; __uzme=5919'
        }
        async with CachedSession(cache=self.cache, expire_after=timedelta(hours=48)) as session:
            response = session.get(url, headers=headers, data=payload, timeout=10)
        if response.from_cache:
            logger.info(f'get_model, created_at: {response.created_at.strftime("%H:%M")}, '
                         f'expires: {response.expires.strftime("%H:%M")}')
        else:
            logger.info(f'Not from cache')
        return response.json()

    def get_search_options(self):
        session = CachedSession('yad2_search_options_cache', backend='sqlite', expire_after=timedelta(hours=48))
        url = ("https://gw.yad2.co.il/search-options/vehicles/cars?fields=manufacturer,year,area,km,ownerID,seats,"
               "engineval,engineType,group_color,gearBox")

        payload = {}
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Cookie': 'leadSaleRentFree=67; y2018-2-cohort=23; __uzma=3c4eec9f-8a37-4503-a6c9-191eba2c7735; '
                      '__uzmb=1691219274; __uzmc=394906189046; __uzmd=1704737848; __uzme=5919'
        }

        response = session.get(url, headers=headers, data=payload, timeout=10)
        return response.json()

    @staticmethod
    def db_path_querystring(query_dict: dict):
        manufacturer_num = query_dict.get('manufacturer', 'multiple_manufacturers')
        model = query_dict.get('model', 'multiple_models')
        manufacturer = num_to_manuf_dict.get(manufacturer_num, 'multiple_manufacturers')
        return f'/car_ads/{manufacturer}/{model}/{query_dict["year"]}/{query_dict["km"]}'

    async def run(self):
        tasks = []
        for url in self.urls:
            q = self.querystring(url)
            task = asyncio.create_task(self.scrape_criteria(q.copy()))
            tasks.append(task)

        data = await asyncio.gather(*tasks)

    async def scrape_criteria(self, query_str: dict):
        first_page = await self.get_first_page(query_str)
        total_items_to_scrape = self.get_total_items(first_page)
        logger.info(f"Total items to be scraped: {total_items_to_scrape} for query: {query_str}")
        last_page = self.get_number_of_pages(first_page)
        feed_sources = FEED_SOURCES_PRIVATE
        car_ads_to_save, feed_items = await self.yad2_scrape(query_str, feed_sources=feed_sources, last_page=last_page)
        # firebase_db.init_firebase_db()
        db_path = self.db_path_querystring(query_str)

        ref = db.reference(db_path)

        data: dict = ref.get()
        if data is None:
            # a dict of dicts in form {car_ad_id: car_ad}
            logging.info("No data in database, creating new data, db_path: {db_path}")
            db.reference(db_path).set({car_ad['id']: car_ad for car_ad in car_ads_to_save})

        for car_ad in car_ads_to_save:
            self.upsert_car_ad(car_ad['id'], car_ad, ref, data)

        self.handle_sold_items(car_ads_to_save, db_path, ref)

        # database.init_db()
        # save_to_database(car_ads_to_save)

    def handle_sold_items(self, scraped_car_ads: list[dict], db_path: str, ref):
        sold_items = []
        car_ads_db = ref.get(shallow=True)
        car_ads: dict = {d.pop('id'): d for d in scraped_car_ads}
        if car_ads_db:
            for key, value in car_ads_db.items():
                if key not in car_ads:
                    car_ad_db: dict = ref.child(key).get()
                    sold_car = {"id": car_ad_db['id'],
                                'price_history': car_ad_db['prices'], 'km': car_ad_db['kilometers'],
                                'year': car_ad_db['year'], 'hand': car_ad_db['hand']}
                    logging.info(f"sold car: {json.dumps(sold_car, ensure_ascii=False)}")
                    sold_items.append(car_ad_db)

            # add sold cars to a separate list
            db_path_for_sold = f'/sold_cars{db_path}'
            try:
                db.reference(db_path_for_sold).update({car_ad['id']: car_ad for car_ad in sold_items})
            except ValueError as e:
                logging.error(f"Error adding sold cars to db: {e}")

            # remove from main db, for next time
            for item in sold_items:
                logging.info(f"removing item {item['id']} from main db")
                db.reference(db_path).child(item['id']).delete()
        return car_ads_db


if __name__ == '__main__':
    firebase_db.init_firebase_db()
    scraper = Scraper(urls)
    logger.info(f"Starting scraper on urls: {urls}")
    asyncio.run(scraper.run())
