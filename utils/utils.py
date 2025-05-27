from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# MongoDB configuration
MONGO_URI = "mongodb+srv://user_admin_sudo:useradminsudo@cluster0.xbak0ji.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "tmr"
COLLECTION_NAME = "tailorMyResume"


def get_resumes_collection():
    """
    Return the MongoDB collection for resumes, configured with Server API v1.
    """
    client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
    db = client[DB_NAME]
    return db[COLLECTION_NAME]