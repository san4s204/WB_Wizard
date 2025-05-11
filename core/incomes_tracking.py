import datetime
from db.database import SessionLocal
from db.models import Income, Token, Product  # Пример имён моделей
from core.wildberries_api import get_incomes
from utils.logger import logger  # Если есть логгер
from utils.token_utils import get_active_tokens
# from config import BASE_URL, etc...

LAST_CHECK_DATETIME = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
PERIOD_DAYS = 90

async def check_new_incomes() -> list[dict]:
    """
    Опрос /incomes, сохраняем новые/обновлённые поставки (Income) в БД.
    Возвращаем список тех поступлений, которые либо новые, либо изменились.
    """

    logger.info("Запуск проверки новых/обновлённых поставок...")
    print("Запуск проверки новых/обновлённых поставок...")
    global LAST_CHECK_DATETIME

    session = SessionLocal()

    # Получаем все токены
    tokens_list = get_active_tokens(session)

    all_new_incomes_dicts = []
    # Период, за который берём поставки (например, последние 90 дней)
    date_from_str = (datetime.datetime.now() - datetime.timedelta(days=PERIOD_DAYS)).strftime("%Y-%m-%d")

    for token_obj in tokens_list:
        token_value = token_obj.token_value
        logger.info(f"Обрабатываем токен id={token_obj.id}")

        # 1) Делаем запрос
        incomes_data = await get_incomes(date_from_str, token_value)
        if not incomes_data:
            continue

        new_or_updated_incomes = []
        max_change_date = LAST_CHECK_DATETIME

        # 2) Обходим ответ
        for data in incomes_data:
            income_id = data.get("incomeId")
            last_change_date_str = data.get("lastChangeDate")

            # Пропускаем, если income_id или lastChangeDate нет
            if not income_id or not last_change_date_str:
                continue

            # Парсим lastChangeDate
            try:
                dt = datetime.datetime.fromisoformat(last_change_date_str)
                # Переводим в UTC (если нужно)
                dt_utc = dt.astimezone(datetime.timezone.utc)
                last_change_date_obj = dt_utc.replace(tzinfo=None)
            except ValueError:
                last_change_date_obj = LAST_CHECK_DATETIME

            # Пытаемся найти существующую запись в БД
            existing_income = (
                session.query(Income)
                .filter_by(income_id=income_id, nm_id=data.get("nmId"), token_id=token_obj.id)
                .first()
            )

            if not existing_income:
                # 3) Создаём новую запись Income
                new_income = Income(
                    token_id=token_obj.id,
                    income_id=income_id,
                    number=data.get("number", ""),
                    date=(
                        parse_datetime(data.get("date"))  # ваша функция parse или datetime.fromisoformat
                        if data.get("date") else None
                    ),
                    last_change_date=last_change_date_obj,
                    supplier_article=data.get("supplierArticle", ""),
                    tech_size=data.get("techSize", ""),
                    barcode=data.get("barcode", ""),
                    quantity=data.get("quantity", 0),
                    total_price=data.get("totalPrice", 0.0),
                    date_close=(
                        parse_datetime(data.get("dateClose"))
                        if data.get("dateClose") else None
                    ),
                    warehouse_name=data.get("warehouseName", ""),
                    nm_id=data.get("nmId"),
                    status=data.get("status", "")
                )
                session.add(new_income)
                session.commit()
                new_or_updated_incomes.append(new_income)
            else:
                # 4) Проверяем, не обновилась ли запись
                #    Если lastChangeDate > existing, считаем что запись обновилась
                if last_change_date_obj > (existing_income.last_change_date or LAST_CHECK_DATETIME):
                    existing_income.last_change_date = last_change_date_obj
                    # Можете обновлять и другие поля, если они могли измениться
                    existing_income.status = data.get("status", existing_income.status)
                    # и т.д...
                    session.commit()
                    new_or_updated_incomes.append(existing_income)

            # Обновляем max_change_date
            if last_change_date_obj > max_change_date:
                max_change_date = last_change_date_obj

        # 5) После обработки всех incomes для данного токена
        session.commit()

        # 6) Формируем список словарей
        #    Аналогично вашему коду check_new_orders,
        #    например, если нужно вернуть наружу
        for inc in new_or_updated_incomes:
            all_new_incomes_dicts.append({
                "token_id": inc.token_id,
                "incomeId": inc.income_id,  # чтобы совпадало с line.get("incomeId")
                "nmId": inc.nm_id,         # чтобы совпадало с line.get("nmId")
                "date": inc.date.isoformat() if inc.date else None,
                "warehouseName": inc.warehouse_name,
                "quantity": inc.quantity,  # теперь будет отображаться в уведомлении
                "totalPrice": inc.total_price,
                "status": inc.status,
            })

        # Обновляем глобальный LAST_CHECK_DATETIME
        LAST_CHECK_DATETIME = max_change_date

    session.close()
    return all_new_incomes_dicts

def parse_datetime(dt_str: str) -> datetime.datetime:
    """
    Вспомогательная функция для парсинга строк вида '2025-03-03T15:41:20'.
    При необходимости добавить логику с timezones, Z-суффиксом и т.п.
    """
    try:
        dt = datetime.datetime.fromisoformat(dt_str)
        # если нужно, приводим к UTC
        dt_utc = dt.astimezone(datetime.timezone.utc)
        return dt_utc.replace(tzinfo=None)
    except ValueError:
        return None
