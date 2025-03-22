# fill_orders.py
import datetime
from typing import List, Dict

from db.database import SessionLocal
from db.models import Order, Token, User
from core.wildberries_api import get_orders  # или где у вас функция get_orders
from sqlalchemy.orm import Session

async def fill_orders(date_from_str: str, telegram_id: str):
    """
    Выполняет единоразовый опрос /orders (WB API) начиная с date_from_str
    и заполняет таблицу orders записями, которых ещё нет.
    Подходит для "первого запуска", чтобы заполнить исторические данные.
    """
    session: Session = SessionLocal()

    # 1. Запрашиваем заказы из WB
    db_user = session.query(User).filter_by(telegram_id=str(telegram_id)).first()

    token_obj = session.query(Token).get(db_user.token_id)

    token_value = token_obj.token_value

    orders_data = await get_orders(date_from_str, token_value, flag=0)  # или какие у вас есть параметры
    if not orders_data:
        print("Нет данных из WB для заполнения orders.")
        session.close()
        return

    count_new = 0
    count_updated = 0

    for data in orders_data:
        srid = data.get("srid")
        if not srid:
            continue

        # Парсим дату lastChangeDate, переводим к UTC-naive
        last_change_date_utc = parse_last_change_date(data.get("lastChangeDate"))
        # Парсим "date"
        date_obj = parse_date_field(data.get("date"))

        # Проверяем, есть ли уже запись
        existing_order = session.query(Order).filter(Order.srid == srid).first()

        if not existing_order:
            # Новый заказ
            new_order = Order(
                token_id=token_obj.id,  # <-- ключевой момент: к какому токену принадлежит
                srid=srid,
                last_change_date=last_change_date_utc,
                date=date_obj,
                warehouse_name=data.get("warehouseName"),
                region_name=data.get("regionName"),
                subject=data.get("subject", ""),
                supplier_article=data.get("supplierArticle", ""),
                techSize=data.get("techSize"),
                full_supplier_article = build_full_supplier_article(
                    data.get("subject", ""), data.get("supplierArticle", "")
                ),
                nm_id=data.get("nmId"),
                brand=data.get("brand"),
                price_with_disc=data.get("priceWithDisc"),
                total_price=data.get("totalPrice"),
                spp=data.get("spp"),
                is_cancel=data.get("isCancel", False)
            )
            session.add(new_order)
            count_new += 1
        else:
            # Обновляем, если изменился lastChangeDate
            if last_change_date_utc and last_change_date_utc > existing_order.last_change_date:
                existing_order.last_change_date = last_change_date_utc
                existing_order.is_cancel = data.get("isCancel", False)
                count_updated += 1

            # Если у нас нет supplier_article, но тут есть
            if not existing_order.supplier_article:
                existing_order.supplier_article = data.get("supplierArticle", "")
                existing_order.full_supplier_article = build_full_supplier_article(
                    existing_order.subject, existing_order.supplier_article
                )
                count_updated += 1

    session.commit()
    session.close()

    print(f"Заполнено orders: новых={count_new}, обновлено={count_updated}")

def parse_last_change_date(last_change_date_str: str):
    """
    Парсим строку вида '2024-11-01T10:11:07' в UTC-naive datetime.
    """
    if not last_change_date_str:
        return None
    try:
        dt = datetime.datetime.fromisoformat(last_change_date_str)  # может быть aware
        # Приводим к UTC
        dt_utc = dt.astimezone(datetime.timezone.utc)
        # Возвращаем naive (но по факту UTC)
        return dt_utc.replace(tzinfo=None)
    except:
        return None

def parse_date_field(date_str: str):
    """
    Поле 'date' в WB может быть '2024-11-01T10:11:07Z'.
    Удаляем 'Z' и парсим.
    """
    if not date_str:
        return None
    date_str = date_str.replace("Z", "")
    try:
        return datetime.datetime.fromisoformat(date_str)
    except:
        return None

def build_full_supplier_article(subject: str, supplier_art: str) -> str:
    """
    Пример объединения subject и supplier_article
    """
    return f"{subject} '{supplier_art}'".strip()
