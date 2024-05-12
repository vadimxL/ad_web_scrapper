import asyncio
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, date
import re
from typing import List, Tuple
import jinja2
import json
import time
from aiohttp_client_cache import CachedSession, SQLiteBackend, CachedResponse
from requests_cache import CachedSession as MyCachedSession
from rich import print
import logging
from car_details import CarDetails
from db_handler import DbHandler
from gmail_sender.gmail_sender import GmailSender
from headers import scrape_headers, model_headers
from models import CarCriteria

logging.getLogger("ad_web_scrapper").addHandler(logging.StreamHandler(stream=sys.stdout))
logger = logging.getLogger("ad_web_scrapper")
logging.basicConfig(
    filename='ad_web_scrapper.log',
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8')

BASE_URL = "https://gw.yad2.co.il/feed-search-legacy/vehicles/cars"

urls = [
    "https://www.yad2.co.il/vehicles/cars?manufacturer=48&model=3866,2829,3484&year=2019--1&km=-1-80000",  # Kia Niro
    "https://www.yad2.co.il/vehicles/cars?manufacturer=27&model=2333&year=2020--1&km=-1-100000",  # Mazda CX-5
    "https://www.yad2.co.il/vehicles/cars?manufacturer=37&model=2842&year=2020--1&km=-1-100000",  # Seat Ateca
    "https://www.yad2.co.il/vehicles/cars?manufacturer=19&model=1428&year=2013-2014&km=0-120000",  # Corola 2013-2014
    "https://www.yad2.co.il/vehicles/cars?manufacturer=21&model=578&year=2020--1&km=-1-100000"  # Hyunadi Tucson
]

urls_expire_after = {
    'yad2.co.il': timedelta(minutes=30),  # Requests for this base URL will expire in a week
}

FEED_SOURCES_PRIVATE = ['private']
FEED_SOURCES_COMMERCIAL = ['commercial', 'xml']
FEED_SOURCES_ALL = ['xml', 'commercial', 'private']

manufacturers_dict = {
    "hyundai": "21",
    "kia": "48",
    "seat": "37",
    "mazda": "27",
    "toyota": "19"
}
num_to_manuf_dict = {value: key for key, value in manufacturers_dict.items()}

models_dict = {
    "tucson": "578",
    "cx5": "2333",
    "ateca": "2842",
    "niro_hybrid": "2829",
    "niro_phev": "3484",
    "niro_plus": "3866",
    "corolla_gli_2013_2016": "1428"
}

num_to_model_dict = {value: key for key, value in models_dict.items()}

secs_to_sleep = 0.1


class Scraper:
    def __init__(self, cache_timeout_min: int):
        # self.db_handler = DbHandler()
        # self.gmail_sender = GmailSender("gmail_sender/credentials.json")
        # self.expiration = timedelta(minutes=30)
        # self.urls_for_expire_after = urls_expire_after
        self.cache = SQLiteBackend(
            cache_name='demo_cache2',
            expire_after=timedelta(minutes=cache_timeout_min),
            urls_expire_after=urls_expire_after,
        )

    async def scrape(self, q: dict) -> CachedResponse:
        url = BASE_URL

        session = CachedSession(cache=SQLiteBackend(
            cache_name='demo_cache2',
            expire_after=timedelta(minutes=30),
            urls_expire_after=urls_expire_after,
        ))
        r: CachedResponse = await session.get(url, data="", headers=scrape_headers, params=q)
        await session.close()

        if r.from_cache:
            logger.info(
                f'cache created_at: {r.created_at.strftime("%H:%M")}, last_used: {r.last_used.strftime("%H:%M:%S")} for page: {q.get("page")}, '
                f'expires: {datetime.fromisoformat(r.expires.isoformat()).strftime("%H:%M:%S") if r.expires else "Never"} ,'
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

        # if not response[0].from_cache:
        #     print(f'Not from cache, sleeping for {secs_to_sleep} second')
        #     time.sleep(secs_to_sleep)

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
            try:
                feed_items = scraped_page['data']['feed']['feed_items']
            except KeyError as e:
                logger.error(f"Error scraping page: {e}")
                with open('json/error_page.json', 'w', encoding='utf-8') as f:
                    json.dump(scraped_page, f, indent=4, ensure_ascii=False)
                raise e

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
            car_details: CarDetails = self.extract_car_details(item)
            car_ads_to_save.append(car_details)

        return car_ads_to_save, filtered_feed_items

    def extract_car_details(self, feed_item: json) -> CarDetails:
        horsepower_value = 0
        row2_without_hp = 'N/A'
        row2 = feed_item.get('row_2', 'N/A')

        # Split the text by lines and process each line
        match = re.search(r'\((.*?)\)', row2)
        if match:
            horsepower_value = match.group(1)
            horsepower_value = re.search(r'\d+', horsepower_value).group(0)
            row2_without_hp = re.sub(r'\([^)]*\)', '', row2)

        hand = self.get_hand(feed_item)

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

        car_details = CarDetails(
            id=feed_item['id'],
            car_model=f"{feed_item['model']} {row2_without_hp}",
            year=feed_item['year'],
            price=price_numeric,
            date_added_epoch=date_added_epoch,
            date_added=formatted_date,
            feed_source=feed_item['feed_source'],

            # Fields with default values
            city=feed_item.get('city', 'N/A'),
            manufacturer_he=feed_item.get('manufacturer', 'N/A'),
            hp=horsepower_value,
            hand=hand,
            kilometers=mileage_numeric,
            prices=[{'price': price_numeric, 'date': date.today().strftime("%d/%m/%Y")}],
            blind_spot=blind_spot,
            smart_cruise_control=smart_cruise_control,
            manuf_en=feed_item.get('manufacturer_eng', 'N/A'),
            gear_type=feed_item.get('Auto_text', 'אוטומט'),
        )

        return car_details

    def get_hand(self, feed_item):
        hand = feed_item.get('Hand_text', 'N/A')
        if "ראשונה" in hand:
            hand = 1
        elif "שניה" in hand:
            hand = 2
        elif "שלישית" in hand:
            hand = 3
        elif "רביעית" in hand:
            hand = 4
        return hand

    @staticmethod
    def querystring(criteria: CarCriteria):
        query = {"manufacturer": criteria.manufacturer,
                 "model": criteria.model,
                 "year": f"{criteria.year_start}-{criteria.year_end}",
                 "km": f"{criteria.km_start}-{criteria.km_end}"}
        if criteria.km_start == -1 and criteria.km_end == -1:
            query.pop("km")
        if criteria.year_start == -1 and criteria.year_end == -1:
            query.pop("year")
        return query

    async def get_model(self, manufacturer_id: str):
        # session = CachedSession('yad2_model_cache', backend='sqlite', expire_after=timedelta(hours=48))
        url = f"https://gw.yad2.co.il/search-options/vehicles/cars?fields=model&manufacturer={manufacturer_id}"

        async with CachedSession(cache=self.cache, expire_after=timedelta(hours=48)) as session:
            response = session.get(url, headers=model_headers, data={}, timeout=10)

        if response.from_cache:
            logger.info(f'get_model, created_at: {response.created_at.strftime("%H:%M")}, '
                        f'expires: {response.expires.strftime("%H:%M")}')
        else:
            logger.info(f'Not from cache')
        return response.json()

    def get_search_options(self):
        session = MyCachedSession('yad2_search_options_cache', backend='sqlite', expire_after=timedelta(hours=48))
        url = ("https://gw.yad2.co.il/search-options/vehicles/cars?fields=manufacturer,year,area,km,ownerID,seats,"
               "engineval,engineType,group_color,gearBox")

        response = session.get(url, headers=model_headers, data={}, timeout=10)
        return response.json()

    async def run(self, query: dict):
        tasks = []
        task = asyncio.create_task(self.scrape_criteria(query.copy()))
        tasks.append(task)

        # Assuming results is a list of tuples, where each tuple contains a list of CarDetails and a query string
        results: List[List[CarDetails]] = await asyncio.gather(*tasks)

        return results[0]

    async def scrape_criteria(self, query_str: dict):
        first_page = await self.get_first_page(query_str)
        total_items_to_scrape = self.get_total_items(first_page)
        logger.info(f"Total items to be scraped: {total_items_to_scrape} for query: {query_str}")
        last_page = self.get_number_of_pages(first_page)
        feed_sources = FEED_SOURCES_PRIVATE
        car_ads_to_save, feed_items = await self.yad2_scrape(query_str, feed_sources=feed_sources, last_page=last_page)
        return car_ads_to_save


if __name__ == '__main__':
    firebase_db.init_firebase_db()
    scraper = Scraper()
    logger.info(f"Starting scraper on urls: {urls}")
    asyncio.run(scraper.run())
