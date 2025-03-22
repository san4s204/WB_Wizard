import datetime
from core.wildberries_api import get_stocks
from db.database import SessionLocal
from db.models import Stock, Token
from sqlalchemy.orm import Session
from utils.logger import logger

# Глобальная переменная для хранения времени последней проверки
LAST_CHECK_DATETIME = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
PERIOD_DAYS = 90

async def check_stocks() -> list[Stock]:
    """
    Опрос /stocks, сохранение новых/обновлённых данных в БД.
    Возвращает список новых или изменённых записей.
    """
    
    logger.info("Запуск проверки остатков товаров...")
    global LAST_CHECK_DATETIME

    session: Session = SessionLocal()

    tokens_list = session.query(Token).all()

    all_new_stocks_dicts = []

    # Формируем dateFrom в формате RFC3339 (UTC)
    date_from_str = (datetime.datetime.now() - datetime.timedelta(days=PERIOD_DAYS)).isoformat()
    for token_obj in tokens_list:
        token_value = token_obj.token_value

        logger.info(f"Обрабатываем токен id={token_obj.id}")

        stocks_data = await get_stocks(date_from_str, token_value)
        if not stocks_data:
            continue

        new_or_updated_stocks = []
        max_change_date = LAST_CHECK_DATETIME

        for data in stocks_data:
            nm_id = data.get("nmId")
            warehouse_name = data.get("warehouseName")
            last_change_date_str = data.get("lastChangeDate")

            if not nm_id or not warehouse_name:
                continue

            quantity = data.get("quantity")
            in_way_to_client = data.get("inWayToClient")

            try:
                dt = datetime.datetime.fromisoformat(last_change_date_str)
                dt_utc = dt.astimezone(datetime.timezone.utc)
                last_change_date_obj = dt_utc.replace(tzinfo=None)
            except ValueError:
                last_change_date_obj = LAST_CHECK_DATETIME

            existing_stock = (
                session.query(Stock)
                .filter_by(nm_id=nm_id, warehouseName=warehouse_name, token_id=token_obj.id)
                .first()
            )

            if not existing_stock:
                logger.debug(f"Новый остаток, NM_ID={nm_id}, склад {warehouse_name}. Сохраняем в БД.")
                new_stock = Stock(
                    token_id=token_obj.id,
                    nm_id=nm_id,
                    warehouseName=warehouse_name,
                    quantity=quantity,
                    last_change_date=last_change_date_obj,
                    quantity_full=data.get("quantityFull"),
                    subject=data.get("subject"),
                    inWayToClient=in_way_to_client,
                )
                session.add(new_stock)
                new_or_updated_stocks.append(new_stock)
            else:
                if last_change_date_obj > existing_stock.last_change_date:
                    logger.debug(f"Остаток NM_ID={nm_id}, склад {warehouse_name} обновился. Обновляем поля.")
                    existing_stock.quantity = quantity
                    existing_stock.inWayToClient = in_way_to_client
                    existing_stock.last_change_date = last_change_date_obj
                    new_or_updated_stocks.append(existing_stock)

            if last_change_date_obj > max_change_date:
                max_change_date = last_change_date_obj

        session.commit()

        for s in new_or_updated_stocks:
            all_new_stocks_dicts.append({
                "token_id": token_obj.id,
                "nm_id": s.nm_id,
                "warehouseName": s.warehouseName,
                "quantity": s.quantity,
                "inWayToClient": s.inWayToClient,
                "last_change_date": s.last_change_date.isoformat(),
                "subject": s.subject,
            })

        LAST_CHECK_DATETIME = max_change_date

    session.close()
    return all_new_stocks_dicts
