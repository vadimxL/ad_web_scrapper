import asyncio
from datetime import datetime, timedelta

import firebase_admin
import json
from firebase_admin import firestore, credentials
import firebase_db
from models import AdDetails
from scraper import Scraper, FEED_SOURCES_COMMERCIAL, FEED_SOURCES_PRIVATE


async def main():
    cred = credentials.Certificate('adscraper.json')
    app = firebase_admin.initialize_app(cred)
    fb_db = firestore.client()

    with open('json/first_page.json', 'r') as f:
        data = json.load(f)
    scraper = Scraper(cache_timeout_min=30)
    ads, _ = await scraper._parse(FEED_SOURCES_PRIVATE, data['data']['feed']['feed_items'])
    ads.sort(key=lambda x: x.date_added, reverse=True)
    for ad in ads:
        diff: timedelta = datetime.now() - ad.date_added
        # returns (minutes, seconds)
        minutes = divmod(diff.total_seconds(), 60)
        print('Total difference in minutes: ', minutes[0], 'minutes',
              minutes[1], 'seconds')
    # for ad in ads:
    #     doc_ref = fb_db.collection("ads").document(ad.id)
    #     doc_ref.set(ad.dict())
    # doc_ref = fb_db.collection("ads").document("alovelace")
    # doc_ref.set({"first": "Ada", "last": "Lovelace", "born": 1815})
    # ref = db.reference('cars/manufacturer=volkswagen,seat,kia,skoda&model=2842,1315,3866,2829,3484,3001&year=2020--1&price=-1-135000&km=-1-80000&hand=0-3&priceOnly=1&imgOnly=1')
    # snapshot: dict = ref.order_by_child('kilometers').start_at(80000).get()
    # for key, value in snapshot.items():
    #     value.pop("full_info")
    #     print(json.dumps(value, indent=4))


if __name__ == '__main__':
    asyncio.run(main())
