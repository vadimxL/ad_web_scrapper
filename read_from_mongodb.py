# Press the green button in the gutter to run the script.
from mongoengine import connect

from scraper import CarAd


def print_db_data():
    for car_ad in CarAd.objects:
        print(car_ad.id)
        for price_history in car_ad.price_history:
            print(price_history.price, price_history.date)


if __name__ == '__main__':
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
        print_db_data()
    except Exception as e:
        print(f"Connection failed: {e}")
        exit()
