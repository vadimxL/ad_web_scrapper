from dotenv import load_dotenv
import os

load_dotenv("backend/secrets/.env")
if "BASE_API_URL" not in os.environ:
    raise Exception("BASE_API_URL not found in environment variables")
if "BASE_OPTIONS_API_URL" not in os.environ:
    raise Exception("BASE_OPTIONS_API_URL not found in environment variables")
if "BASE_URL" not in os.environ:
    raise Exception("BASE_URL not found in environment variables")
if "BASE_CATALOG_API_URL" not in os.environ:
    raise Exception("BASE_CATALOG_API_URL not found in environment variables")
if "BASE_API_CAR_AD_URL" not in os.environ:
    raise Exception("BASE_API_CAR_AD_URL not found in environment variables")
if "FIREBASE_DB_URL" not in os.environ:
    raise Exception("FIREBASE_DB_URL not found in environment variables")
if "FIREBASE_CERTIFICATE_PATH" not in os.environ:
    raise Exception("FIREBASE_CERTIFICATE_PATH not found in environment variables")

BASE_API_URL: str = os.environ.get("BASE_API_URL")
BASE_OPTIONS_API_URL: str = os.environ.get("BASE_OPTIONS_API_URL")
BASE_CATALOG_API_URL: str = os.environ.get("BASE_CATALOG_API_URL")
BASE_URL: str = os.environ.get("BASE_URL")
BASE_API_CAR_AD_URL: str = os.environ.get("BASE_API_CAR_AD_URL")
FIREBASE_DB_URL: str = os.environ.get("FIREBASE_DB_URL")
FIREBASE_CERTIFICATE_PATH: str = os.environ.get("FIREBASE_CERTIFICATE_PATH")