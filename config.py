import os
from dotenv import load_dotenv
from dataclasses import dataclass
load_dotenv(override=True)  # Если используем .env

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


@dataclass(frozen=True)
class Tariff:
    code: str
    title: str
    amount_rub: str   # строкой, как любит ЮKassa: "349.00"
    duration_days: int
    role: str         # во что переводим Token.role

TARIFFS = {
    "base": Tariff(code="base", title="Base", amount_rub="349.00", duration_days=30, role="base"),
    "advanced": Tariff(code="advanced", title="Advanced", amount_rub="949.00", duration_days=30, role="advanced"),
}