import asyncio
from datetime import datetime, timedelta
import re
from typing import List
import json
import time
from aiohttp_client_cache import CachedSession, SQLiteBackend, CachedResponse
from requests_cache import CachedSession as MyCachedSession
from rich import print
from car_details import CarDetails, PriceHistory
from handz import Handz
from headers import scrape_headers, model_headers
from logger_setup import internal_info_logger


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
            internal_info_logger.info(
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
                internal_info_logger.error(f"Error scraping page: {e}")
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

        internal_info_logger.info(f"Skipped {no_id_items_num} items because they don't have an id")
        internal_info_logger.info(f"Skipped {incompatible_feed_sources_items_num} items because they are not in {feed_sources} list")

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
            )
        except Exception as e:
            internal_info_logger.error(f"Error extracting car details: {e}")
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
    async def get_model(manufacturer_id: str):
        session = MyCachedSession('yad2_model_cache', backend='sqlite', expire_after=timedelta(hours=48))
        url = f"https://gw.yad2.co.il/search-options/vehicles/cars?fields=model&manufacturer={manufacturer_id}"

        response = session.get(url, headers=model_headers, data={}, timeout=10)
        return response.json()

    @staticmethod
    def get_search_options():
        session = MyCachedSession('yad2_search_options_cache', backend='sqlite', expire_after=timedelta(hours=48))
        url = ("https://gw.yad2.co.il/search-options/vehicles/cars?fields=manufacturer,year,area,km,ownerID,seats,"
               "engineval,engineType,group_color,gearBox")

        response = session.get(url, headers=model_headers, data={}, timeout=10)
        return response.json()

    def run(self, query: dict, loop):
        # Assuming results is a list of tuples, where each tuple contains a list of CarDetails and a query string
        q: dict = query.copy()
        future = asyncio.run_coroutine_threadsafe(self.scrape_criteria(q), loop)
        try:
            result = future.result(timeout=60)
        except TimeoutError:
            print('The coroutine took too long, cancelling the task...')
            future.cancel()
        except Exception as exc:
            print(f'The coroutine raised an exception: {exc!r}')
        else:
            print(f'The coroutine returned successfully')
        return result

    async def scrape_criteria(self, query_str: dict):
        first_page = await self.first_page(query_str)
        total_items_to_scrape = self.get_total_items(first_page)
        internal_info_logger.info(f"Total items to be scraped: {total_items_to_scrape} for query: {query_str}")
        last_page = self.get_number_of_pages(first_page)
        feed_sources = FEED_SOURCES_PRIVATE
        car_ads_to_save, feed_items = await self.yad2_scrape(query_str, feed_sources=feed_sources, last_page=last_page)
        internal_info_logger.info(f"Scraped {len(car_ads_to_save)} items for query: {query_str}, feed_sources: {feed_sources}")
        return car_ads_to_save


if __name__ == '__main__':
    pass
