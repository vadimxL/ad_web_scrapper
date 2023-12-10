# This is a sample Python script.
from datetime import datetime, timedelta
import re

import pandas as pd

import database
import json
import time
from requests_cache import CachedSession, CachedResponse
from rich import print
from mongoengine import connect, StringField, IntField, EmbeddedDocument

from handz import get_pricing_from_handz

manufacturers_dict = {
    "hyundai": "21",
    "kia": "48",
    "seat": "37"
}

secs_to_sleep = 0.5


def scrape(parsed_feed_items: list, querystring, session) -> CachedResponse:
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

    r = session.get(url, data=payload, headers=headers, params=querystring)

    # print(
    #     r.from_cache,
    #     r.created_at,
    #     r.expires,
    #     r.is_expired,
    # )

    scraped_page = r.json()
    feed_items = scraped_page['data']['feed']['feed_items']
    for feed_item in feed_items:
        # car_details = extract_car_details(feed_item)
        car_details = dict(sorted(feed_item.items()))
        parsed_feed_items.append(car_details)

    return r


def get_first_page(querystring: dict):
    session = CachedSession('yad2_first_page_cache', backend='sqlite',
                            expire_after=timedelta(hours=3))
    querystring['page'] = str(1)
    parsed_feed_items = []  # type: list
    # Use a breakpoint in the code line below to debug your script.
    response = scrape(parsed_feed_items, querystring, session)
    if not response.from_cache:
        print(f'Not from cache, sleeping for {secs_to_sleep} second')
        time.sleep(secs_to_sleep)

    with open('json/first_page.json', 'w', encoding='utf-8') as f1:
        json.dump(response.json(), f1, indent=4, ensure_ascii=False)

    return response.json()


def get_number_of_pages(querystring: dict):
    first_page = get_first_page(querystring)
    # print(f"Total items to be scraped: {first_page['data']['pagination']['total_items']}")
    return first_page['data']['pagination']['last_page']
    # print(f"Last page: {last_page}")


def get_total_items(querystring: dict):
    first_page = get_first_page(querystring)
    # print(f"Total items to be scraped: {first_page['data']['pagination']['total_items']}")
    return first_page['data']['pagination']['total_items']
    # last_page = scraped_page['data']['pagination']['last_page']
    # print(f"Last page: {last_page}")


def yad2_scrape(querystring: dict, feed_sources, last_page: int = 1):
    parsed_feed_items = []  # type: list
    filtered_feed_items = []  # type: list
    car_ads_to_save = []
    session = CachedSession('yad2_cache', backend='sqlite', expire_after=timedelta(hours=3))
    for i in range(1, last_page + 1):
        print(f'scraping page {i}')
        querystring['page'] = str(i)
        result = scrape(parsed_feed_items, querystring, session)
        if not result.from_cache:
            print(f'Not from cache, sleeping for {secs_to_sleep} second')
            time.sleep(secs_to_sleep)

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
        car_ads_to_save.append(extract_car_details(item))

    handz_result = get_pricing_from_handz(filtered_feed_items, "62e8c1a08efe2d1fad068684")

    for res in handz_result['data']['entities']:
        result_filter = next(filter(lambda x: x['id'] == res['id'], car_ads_to_save), None)
        if result_filter:
            result_filter['prices'] = res['prices']
            result_filter['dateCreated'] = res['dateCreated']

    # Assuming car_ads_to_save is a list of dictionaries
    manufacturers = set(ad['manufacturer'] for ad in car_ads_to_save)
    if len(manufacturers) == 1:
        manufacturer = manufacturers.pop()
    else:
        manufacturer = "multiple"

    filename_json = f'json/car_ads_{manufacturer}_{"_".join(feed_sources)}_' + datetime.now().strftime(
        "%Y_%m_%d_%H") + '.json'
    filename_csv = f'json/car_ads_{manufacturer}_{"_".join(feed_sources)}_' + datetime.now().strftime("%Y_%m_%d_%H")
    with open(filename_json, 'w', encoding='utf-8') as f1:
        json.dump(car_ads_to_save, f1, indent=4, ensure_ascii=False)

    df = pd.json_normalize(car_ads_to_save, ['prices'],
                           ['id', 'manufacturer', 'car_model', 'year', 'hand',
                            'kilometers', 'current_price', 'updated_at', 'date_added'])

    with open(filename_csv + ".csv", 'w') as f:
        df.to_csv(f, index=False, header=True, encoding='utf-8-sig')

    return car_ads_to_save


def extract_car_details(feed_item: json):
    horsepower_value = 'N/A'
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

    car_details = {
        'id': feed_item['id'],
        'feed_source': feed_item['feed_source'],
        'city': feed_item.get('city', 'N/A'),
        'manufacturer_he': feed_item.get('manufacturer', 'N/A'),
        'car_model': f"{feed_item['model']} {row2_without_hp}",
        'hp': horsepower_value,
        'year': feed_item['year'],
        'hand': hand,
        # 'engine_size': feed_item.get('EngineVal_text', 0),
        'kilometers': feed_item['kilometers'],
        'current_price': feed_item['price'],
        'updated_at': feed_item['updated_at'],
        'date_added': feed_item['date_added'],
        'manufacturer': feed_item.get('manufacturer_eng', 'N/A'),
        # 'description': feed_item['search_text']
    }

    return car_details


def url_to_querystring(url: str):
    querystring = {}
    for param in url.split('?')[1].split('&'):
        key, value = param.split('=')
        querystring[key] = value
    return querystring


def main():
    FEED_SOURCES_PRIVATE = ['private']
    FEED_SOURCES_COMMERCIAL = ['commercial', 'xml']
    FEED_SOURCES_ALL = ['xml', 'commercial', 'private']

    url = "https://www.yad2.co.il/vehicles/cars?carFamilyType=2,3,4,5,8,9,10&year=2020-2024&price=95000-135000&km=1000-40000&engineval=1400--1&priceOnly=1&imgOnly=1"

    querystring = url_to_querystring(url)

    total_items_to_scrape = get_total_items(querystring)
    print(f"Total items to be scraped: {total_items_to_scrape}")
    last_page = get_number_of_pages(querystring)
    print(f"Last page: {last_page}")
    car_ads_to_save = yad2_scrape(querystring, feed_sources=FEED_SOURCES_PRIVATE, last_page=last_page)
    # database.init_db()
    # save_to_database(car_ads_to_save)


if __name__ == '__main__':
    main()
