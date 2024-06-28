import os
import json
from mongoengine import connect

from models import CarAd, PriceHistory


def save_to_database(car_ads: list):
    for details in car_ads:
        ad = CarAd(id=details['id'])
        ad.manufacturer = details['manufacturer']
        ad.model = details['car_model']
        ad.year = details['year']
        ad.hand = details['hand']
        ad.engine_size = details['engine_size']
        ad.kilometers = details['kilometers']
        ad.price = details['price']
        ad.updated_at = details['updated_at']
        ad.date_added = details['date_added']
        for date_price in details['prices']:
            ad.price_history.append(PriceHistory(price=date_price['price'], date=date_price['date']))
        ad.save()


def init_from_persistance():
    # load all json file from json folder
    # for each file, load the json and save to db

    # Iterate over each JSON file in the folder
    for filename in os.listdir('json'):
        if filename.endswith('.json'):
            filepath = os.path.join('json', filename)

            # Read and parse the JSON content
            with open(filepath, 'r') as file:
                json_content = json.load(file)

            # Insert the item from the JSON file into the MongoDB collection
            save_to_database(json_content)


def init_db():
    try:
        # Connect to the MongoDB database
        connections = connect(
            db="scraper_db",
            host="localhost",
            port=27018,
            username="root",
            password="example",
            authentication_source="admin"
        )
        print(f"Connected to MongoDB: {connections}")
        init_from_persistance()
    except Exception as e:
        print(f"Connection failed: {e}")
        exit()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    init_db()
    init_from_persistance()
