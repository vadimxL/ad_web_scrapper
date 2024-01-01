import firebase_admin
from firebase_admin import credentials
from firebase_admin import db


def init_firebase_db():
    databaseURL = "https://carscraper-d91d9-default-rtdb.firebaseio.com/"
    cred = credentials.Certificate("firebase_admin_key.json")
    default_app = firebase_admin.initialize_app(cred, {
        'databaseURL': databaseURL
    })


def clear_firebase_db():
    ref = db.reference('/')
    ref.delete()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    init_firebase_db()
