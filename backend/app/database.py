import os
import pymongo

MONGODB_URI = os.getenv("MONGODB_URI")
if MONGODB_URI:
    client = pymongo.MongoClient(MONGODB_URI)
else:
    try:
        import mongomock
        client = mongomock.MongoClient()
    except ImportError:
        client = pymongo.MongoClient("mongodb://localhost:27017/classroom")

try:
    db = client.get_default_database()
except Exception:
    db = client["classroom"]

def get_db():
    yield db
