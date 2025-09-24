import os
from typing import Any

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from pyparsing import Optional


def init_firebase_db() -> Any:
    database_url: Optional[str] = os.environ.get("FIREBASE_DB_URL")
    certificate_path: Optional[str] = os.environ.get("FIREBASE_CERTIFICATE_PATH")
    if database_url is None or certificate_path is None:
        raise ValueError("FIREBASE_DB_URL and FIREBASE_CERTIFICATE_PATH must be set in environment variables")
    cred = credentials.Certificate(certificate_path)
    default_app: firebase_admin.App = firebase_admin.initialize_app(cred, {
        'databaseURL': database_url
    })
    print("Firebase DB initialized, default app name:", default_app.name)
    return db


def clear_firebase_db():
    ref = db.reference('/')
    ref.delete()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    init_firebase_db()
