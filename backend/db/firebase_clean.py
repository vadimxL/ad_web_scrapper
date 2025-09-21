from firebase_admin import db
from firebase_db import init_firebase_db

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    init_firebase_db()
    ref = db.reference('/')
    ref.delete()
    print("done")