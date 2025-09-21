import os

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db


def init_firebase_db():
    database_url: str = os.environ.get("FIREBASE_DB_URL")
    certificate_path: str = os.environ.get("FIREBASE_CERTIFICATE_PATH")
    cred = credentials.Certificate(certificate_path)
    default_app: firebase_admin.App = firebase_admin.initialize_app(cred, {
        'databaseURL': database_url
    })
    print("Firebase DB initialized, default app name:", default_app.name)


def clear_firebase_db():
    ref = db.reference('/')
    ref.delete()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    init_firebase_db()
