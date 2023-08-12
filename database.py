from mongoengine import connect


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
    except Exception as e:
        print(f"Connection failed: {e}")
        exit()
