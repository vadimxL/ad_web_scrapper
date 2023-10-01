import os
import json
from mongoengine import connect

from models import CarAd, PriceHistory


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
            db="favorites_yad2",
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
