import os
from dotenv import load_dotenv

load_dotenv()  # Если используем .env

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WB_API_KEY = os.getenv("WB_API_KEY")  # когда получим
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")
DB_NAME = os.getenv("DB_NAME", "WB_Wizard_db")

YANDEX_MERCHANT_ID = os.getenv("YANDEX_MERCHANT_ID")
YANDEX_SECRET_KEY = os.getenv("YANDEX_SECRET_KEY")
...
