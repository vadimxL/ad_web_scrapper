import asyncio
import os
from datetime import datetime, timedelta
import re
from typing import List, Dict, Tuple
from urllib.parse import urlparse

import requests

import json
import time
from aiohttp_client_cache import CachedSession, SQLiteBackend, CachedResponse
from requests_cache import CachedSession as MyCachedSession
from car_details import CarDetails, PriceHistory
from handz.handz import Handz
from headers import scrape_headers, model_headers
from logger_setup import internal_info_logger as logger
from dotenv import load_dotenv


load_dotenv()
if "BASE_API_URL" not in os.environ:
    raise Exception("BASE_API_URL not found in environment variables")
if "BASE_OPTIONS_API_URL" not in os.environ:
    raise Exception("BASE_OPTIONS_API_URL not found in environment variables")
if "BASE_URL" not in os.environ:
    raise Exception("BASE_URL not found in environment variables")

BASE_API_URL: str = os.environ.get("BASE_API_URL")
BASE_OPTIONS_API_URL: str = os.environ.get("BASE_OPTIONS_API_URL")
BASE_URL: str = os.environ.get("BASE_URL")


FEED_SOURCES_ALL = ['xml', 'commercial', 'private']
FEED_SOURCES_PRIVATE = FEED_SOURCES_ALL[2]
FEED_SOURCES_COMMERCIAL = FEED_SOURCES_ALL[1:2]

secs_to_sleep = 0.1


class Scraper:
    def __init__(self, cache_timeout_min: int):
        self.cache = SQLiteBackend(
            cache_name='cache/scrape_cache',
            expire_after=timedelta(minutes=cache_timeout_min),
        )

    async def scrape(self, q: dict) -> CachedResponse:
        url = BASE_API_URL

        session = CachedSession(cache=SQLiteBackend(
            cache_name='cache/scrape_cache',
            expire_after=timedelta(minutes=30),
        ))
        r: CachedResponse = await session.get(url, data="", headers=scrape_headers, params=q)
        await session.close()

        if r.from_cache:
            logger.info(
                f'cache created_at: {r.created_at.strftime("%H:%M")}, last_used: {r.last_used.strftime("%H:%M:%S")} for page: {q.get("page")}, '
                f'expires: {datetime.fromisoformat(r.expires.isoformat()).strftime("%H:%M:%S") if r.expires else "Never"} ,'
                f'url: {url}, query: {q}')

        return r

    async def first_page(self, q: dict) -> dict:
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

        json_response = await response[0].json()

        with open('json/first_page.json', 'w', encoding='utf-8') as f1:
            json.dump(json_response, f1, indent=4, ensure_ascii=False)

        return json_response

    def get_number_of_pages(self, first_page):
        return first_page['data']['pagination']['last_page']

    def get_total_items(self, first_page):
        return first_page['data']['pagination']['total_items']

    async def _scrape(self, q: dict, feed_sources, last_page: int = 1):
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
                logger.info(f'Not from cache, sleeping for {secs_to_sleep} second')
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

        no_id_items_num = 0
        incompatible_feed_sources_items_num = 0
        for item in parsed_feed_items:
            # if item['type'] != 'ad':
            #     # print(f"Skipping item {car_details['type']} because it's not an ad")
            #     continue
            #
            if 'id' not in item:
                no_id_items_num += 1
                continue

            if item['feed_source'] not in feed_sources:
                incompatible_feed_sources_items_num += 1
                continue

            filtered_feed_items.append(item)
            car_details: CarDetails = self.extract_car_details(item)
            car_ads_to_save.append(car_details)

        logger.info(f"Skipped {no_id_items_num} items because they don't have an id")
        logger.info(f"Skipped {incompatible_feed_sources_items_num} items because they are not in {feed_sources} list")

        handz = Handz()
        divided_feed_items = list(self.divide_chunks(filtered_feed_items, 50))
        handz_results = []
        for divided_feed_item in divided_feed_items:
            handz_result = handz.get_prices(divided_feed_item)
            handz_results.extend(handz_result['data']['entities'])

        for res in handz_results:
            result_filter: CarDetails = next(filter(lambda x: x.id == res['id'], car_ads_to_save), None)
            if result_filter:
                result_filter.prices_handz = self.convert_data_to_string(res['prices'])

        return car_ads_to_save, filtered_feed_items

    # Function to convert and simplify the data
    # Function to convert and simplify the data
    # Function to convert and simplify the data into a single string
    def convert_data_to_string(self, data):
        lines = []
        for item in data:
            # Parse the date and format it to a simpler date format (e.g., YYYY-MM-DD)
            parsed_date = datetime.fromisoformat(item['date'].replace('Z', '+00:00'))
            simplified_date = parsed_date.strftime('%Y-%m-%d')  # Simplified date format

            # Get the price, handle None case
            price = str(item['price']) if item['price'] is not None else 'None'

            # Create the string with date and price separated by '|'
            line = f"{simplified_date} {price}"

            # Add the string to the list of lines
            lines.append(line)

        # Join all lines into a single string with new line separators
        result_string = '| '.join(lines)

        return result_string

    # Yield successive n-sized
    # chunks from l.
    def divide_chunks(self, listing: List, n: int):
        # looping till length l
        for i in range(0, len(listing), n):
            yield listing[i:i + n]

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

        #  get the test date
        test_date = 'N/A'
        for item in feed_item['more_details']:
            if item['name'] == 'testDate':
                test_date = item['value']

        # get month on a road
        month_on_road = 'N/A'
        for item in feed_item['more_details']:
            if item['name'] == 'month':
                month_on_road = item['value']

        try:
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
                prices=[PriceHistory(price=price_numeric, date=datetime.now())],
                blind_spot=blind_spot,
                smart_cruise_control=smart_cruise_control,
                manuf_en=feed_item.get('manufacturer_eng', 'N/A'),
                gear_type=self.gear_type(feed_item),
                test_date=test_date,
                month_on_road=month_on_road,
                full_info=feed_item
            )
        except Exception as e:
            logger.error(f"Error extracting car details: {e}")
            with open('json/error_feed_item.json', 'w', encoding='utf-8') as f:
                json.dump(feed_item, f, indent=4, ensure_ascii=False)
            raise e

        return car_details

    def gear_type(self, feed_item):
        gear_type = feed_item.get('Auto_text', 'N/A')
        if "אוטומט" in gear_type:
            gear_type = "automatic"
        elif "ידני" in gear_type:
            gear_type = "manual"
        return gear_type

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
        elif "חמישית" in hand:
            hand = 5
        elif "מיבואן" in hand:
            hand = 0
        return hand

    @staticmethod
    def search_by_value(data, target_value):
        for item in data:
            if item["value"] == target_value:
                return item["text"]
        return None  # Return None if the value is not found

    @staticmethod
    async def get_meta(manufacturers_: str, models_: str, submodels: str):
        models_list: List[str] = models_.split(",")
        submodels_list: List[str] = submodels.split(",")
        manufacturers_list: List[str] = manufacturers_.split(",")
        model_names = []
        submodel_names = []
        manufacturers_names = []
        data = await Scraper.get_search_options(manufacturers_)
        for manufacturer in manufacturers_list:
            manufacturer_name = Scraper.search_by_value(data['data']['manufacturer'], manufacturer)
            if manufacturer_name:
                manufacturers_names.append(manufacturer_name)
        for model_value in models_list:
            model_name = Scraper.search_by_value(data['data']['model'], model_value)
            if model_name:
                model_names.append(model_name)
        for submodel_value in submodels_list:
            submodel_name = Scraper.search_by_value(data['data']['subModel'], submodel_value)
            if submodel_name:
                submodel_names.append(submodel_name)

        return manufacturers_names, model_names, submodel_names

    @staticmethod
    async def get_model(manufacturer_id: str):
        session = MyCachedSession('cache/model_cache', backend='sqlite', expire_after=timedelta(days=4))
        url = f"{BASE_OPTIONS_API_URL}?fields=model&manufacturer={manufacturer_id}"

        response = session.get(url, headers=model_headers, data={}, timeout=10)
        return response.json()

    @staticmethod
    async def get_submodel(model_id: str):
        session = MyCachedSession('cache/model_cache', backend='sqlite', expire_after=timedelta(days=4))
        url = f"{BASE_OPTIONS_API_URL}?fields=subModel&model={model_id}"

        response = session.get(url, headers=model_headers, data={}, timeout=10)
        return response.json()

    @staticmethod
    async def get_search_options(manufacturers: str):  # a comma separated string of manufacturers,
        # example: "21,48,37,27,19"
        session = MyCachedSession('cache/search_options_cache', backend='sqlite', expire_after=timedelta(days=4))
        url = f"{BASE_OPTIONS_API_URL}?fields=manufacturer,model,subModel&manufacturer={manufacturers}"

        response = session.get(url, headers=model_headers, data={}, timeout=10)
        return response.json()

    def run(self, query: dict) -> Tuple[List[CarDetails], List[dict]]:
        # Assuming results is a list of tuples, where each tuple contains a list of CarDetails and a query string
        q: dict = query.copy()
        result = asyncio.new_event_loop().run_until_complete(self.scrape_criteria(q))
        return result

    async def scrape_criteria(self, query_str: dict):
        first_page = await self.first_page(query_str)
        total_items_to_scrape = self.get_total_items(first_page)
        logger.info(f"Total items to be scraped: {total_items_to_scrape} for query: {query_str}")
        last_page = self.get_number_of_pages(first_page)
        feed_sources = FEED_SOURCES_PRIVATE
        car_ads_to_save, feed_items = await self._scrape(query_str, feed_sources=feed_sources, last_page=last_page)
        logger.info(f"Scraped {len(car_ads_to_save)} items for query: {query_str}, feed_sources: {feed_sources}")
        # self.save_feed_items(feed_items)
        return car_ads_to_save, feed_items


if __name__ == '__main__':
    pass
