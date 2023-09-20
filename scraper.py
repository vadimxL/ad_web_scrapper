# This is a sample Python script.
import re
from datetime import timedelta

import database
import json
import time
from requests_cache import CachedSession
from rich import print
from handz import get_pricing_from_handz
from models import CarAd, PriceHistory
from normalize_json import normalize_json

manufacturers_dict = {
    "hyundai": "21",
    "kia": "48",
    "seat": "37"
}


def scrape(parsed_feed_items: list, querystring, session):
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

    print(f'{r.from_cache=}, created at={r.created_at.strftime("%m/%d/%Y, %H:%M:%S")}, '
          f'expires at={r.expires.strftime("%m/%d/%Y, %H:%M:%S")}, {r.is_expired=}')

    scraped_page = r.json()
    feed_items = scraped_page['data']['feed']['feed_items']
    for feed_item in feed_items:
        if feed_item['type'] != 'ad':
            continue

        if feed_item['feed_source'] != 'private':
            continue

        # car_details = extract_car_details(feed_item)
        car_details = dict(sorted(feed_item.items()))
        parsed_feed_items.append(car_details)

    if not r.from_cache:
        print(f'Not from cache, sleeping for 1 second')
        time.sleep(1)

    return scraped_page


def handle_handz_results(parsed_feed: list, token, split_size=500) -> list:
    # Assuming parsed_feed_items is a list

    # Check if parsed_feed_items has more than 500 items
    if len(parsed_feed) > split_size:
        chunk_size = split_size
        num_chunks = len(parsed_feed) // chunk_size + (len(parsed_feed) % chunk_size > 0)

        # Initialize an empty list to store results
        handz_result = []

        # Split parsed_feed_items into chunks and process each chunk
        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(parsed_feed))
            chunk = parsed_feed[start_idx:end_idx]

            # Process the chunk using get_pricing_from_handz
            chunk_result = get_pricing_from_handz(chunk, token)
            handz_result.extend(chunk_result['data']['entities'])
    else:
        # If parsed_feed_items has 500 or fewer items, process all at once
        handz_result = get_pricing_from_handz(parsed_feed, token)['data']['entities']

    return handz_result


def yad2_scrape(querystring: dict):
    session = CachedSession('yad2_cache', backend='sqlite', expire_after=timedelta(hours=5))

    page_num = 1
    querystring['page'] = str(page_num)
    parsed_feed_items = []  # type: list
    # Use a breakpoint in the code line below to debug your script.
    scraped_page = scrape(parsed_feed_items, querystring, session)
    car_ads = scraped_page['data']['feed']['feed_items']

    with open('json/first_page.json', 'w', encoding='utf-8') as f1:
        json.dump(car_ads, f1, indent=4, ensure_ascii=False)

    print(f"Total items to be scraped: {scraped_page['data']['pagination']['total_items']}")
    last_page = scraped_page['data']['pagination']['last_page']
    print(f"Last page: {last_page}")
    for i in range(2, last_page + 1):
        print(f'page {i}')
        querystring['page'] = str(i)
        scrape(parsed_feed_items, querystring, session)

    car_ads_to_save_ = []
    # save_to_database(parsed_feed_items)
    for car_details in parsed_feed_items:
        car_ads_to_save_.append(extract_car_details(car_details))

    handz_result = handle_handz_results(parsed_feed_items, token="62e8c1a08efe2d1fad068684", split_size=300)

    for res in handz_result:
        result_filter = next(filter(lambda x: x['id'] == res['id'], car_ads_to_save_), None)
        if result_filter:
            result_filter['prices'] = res['prices']
            result_filter['dateCreated'] = res['dateCreated']

    with open('json/car_ads.json', 'w', encoding='utf-8') as f1:
        json.dump(car_ads_to_save_, f1, indent=4, ensure_ascii=False)
    normalize_json(car_ads_to_save_, 'json/car_ads_normalized')
    return car_ads_to_save_


def save_to_database(car_ads: list):
    for car_details in car_ads:
        car_ad = CarAd(id=car_details['id'])
        car_ad.manufacturer = car_details['manufacturer']
        car_ad.model = car_details['car_model']
        car_ad.year = car_details['year']
        car_ad.hand = car_details['hand']
        car_ad.engine_size = car_details['engine_size']
        car_ad.kilometers = car_details['kilometers']
        car_ad.price = car_details['price']
        car_ad.updated_at = car_details['updated_at']
        car_ad.date_added = car_details['date_added']
        for date_price in car_details['prices']:
            car_ad.price_history.append(PriceHistory(price=date_price['price'], date=date_price['date']))
        car_ad.save()


def extract_car_details(feed_item: json):
    date_pattern = r"\d{2}/\d{2}/\d{4}"
    match = re.search(date_pattern, feed_item['updated_at'])
    # Extract the matched date
    extracted_date = feed_item['updated_at']
    if match:
        extracted_date = match.group()

    car_details = {
        'id': feed_item['id'],
        'city': feed_item.get('city', 'N/A'),
        'manufacturer': feed_item.get('manufacturer_eng', 'N/A'),
        'car_model': feed_item['model'],
        'year': feed_item['year'],
        'hand': feed_item['Hand_text'],
        'engine_size': feed_item.get('EngineVal_text', 0),
        'kilometers': feed_item['kilometers'],
        'price': feed_item['price'],
        'updated_at': extracted_date,
        'date_added': feed_item['date_added']
        # 'description': feed_item['search_text']
    }

    return car_details


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    hyundai_querystring = {"year": "2020--1", "price": "80000-135000", "km": "500-40000", "hand": "-1-2",
                           "priceOnly": "1",
                           "imgOnly": "1", "page": "1", "manufacturer": manufacturers_dict['hyundai'],
                           "carFamilyType": "10,5", "forceLdLoad": "true"}

    kia_querystring = {"year": "2020--1", "price": "-1-135000", "km": "500-60000", "hand": "-1-2",
                       "priceOnly": "1", "model": "2829,3484,3223,3866",
                       "imgOnly": "1", "page": "1", "manufacturer": manufacturers_dict['kia'],
                       "carFamilyType": "10,5", "forceLdLoad": "true"}

    suv_querystring = {"year": "2020--1", "price": "-1-135000", "km": "500-60000", "hand": "-1-2",
                       "priceOnly": "1", "imgOnly": "1", "page": "1",
                       "carFamilyType": "10,5", "forceLdLoad": "true"}

    car_ads_to_save = yad2_scrape(suv_querystring)
    database.init_db()
    save_to_database(car_ads_to_save)
