import datetime
from core.wildberries_api import get_orders
from db.database import SessionLocal
from db.models import Order, Product, Token
from sqlalchemy.orm import Session
from utils.logger import logger
from utils.token_utils import get_active_tokens  # Импортируем функцию для получения активных токенов
from core.products_service import upsert_product

# Можно где-то хранить в памяти или в отдельной таблице. Для примера -- глобально:
LAST_CHECK_DATETIME = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
PERIOD_DAYS = 7
async def check_new_orders() -> list[dict]:
    """
    Опрос /orders, сохраняем новые/обновлённые заказы в БД.
    Возвращаем список тех заказов, которые либо новые, либо изменились.
    """

    logger.info("Запуск проверки новых/обновлённых заказов...")
    global LAST_CHECK_DATETIME

    
    session: Session = SessionLocal()

    tokens_list = get_active_tokens(session)

    all_new_orders_dicts = []

    date_from_str = (datetime.datetime.now() - datetime.timedelta(days=PERIOD_DAYS)).isoformat()

    for token_obj in tokens_list:
        token_value = token_obj.token_value

        logger.info(f"Обрабатываем токен id={token_obj.id}")

        # Делаем запрос
        orders_data = await get_orders(date_from_str, token_value, flag=0)
        if not orders_data:
            continue
        
        logger.info(f"Token_id={token_obj.id}, получено {len(orders_data)} заказов.")
        new_or_updated_orders = []
        max_change_date = LAST_CHECK_DATETIME

        for data in orders_data:
            srid = data.get("srid")
            last_change_date_str = data.get("lastChangeDate")
            if not srid or not last_change_date_str:
                continue

            try:
                dt = datetime.datetime.fromisoformat(last_change_date_str)
                dt_utc = dt.astimezone(datetime.timezone.utc)
                last_change_date_obj = dt_utc.replace(tzinfo=None)
            except ValueError:
                last_change_date_obj = LAST_CHECK_DATETIME

            existing_order = session.query(Order).filter_by(srid=srid, token_id=token_obj.id).first()

            subject = data.get("subject", "")
            supplier_art = data.get("supplierArticle", "")
            tech_size = data.get("techSize", "")

            product_in_db = session.query(Product).filter_by(nm_id=nm_id).first()

            if product_in_db is None:
                # upsert_product — асинхронная, поэтому обязательно await
                await upsert_product(
                    nm_id           = nm_id,
                    subject_name    = subject,
                    brand_name      = data.get("brand"),
                    supplier_article= supplier_art,
                    token_id        = token_obj.id,
                    techSize        = tech_size
                )

            if not existing_order:
                # Новый заказ
                new_order = Order(
                    token_id=token_obj.id,
                    srid=srid,
                    last_change_date=last_change_date_obj,
                    date=(
                        datetime.datetime.fromisoformat(data["date"].replace("Z", ""))
                        if data.get("date") else None
                    ),
                    warehouse_name=data.get("warehouseName"),
                    region_name=data.get("regionName"),
                    subject=subject,
                    supplier_article=supplier_art,
                    full_supplier_article=f"{subject} '{supplier_art}'".strip(),
                    nm_id=data.get("nmId"),
                    brand=data.get("brand"),
                    techSize=tech_size,
                    price_with_disc=data.get("priceWithDisc"),
                    total_price=data.get("totalPrice"),
                    spp=data.get("spp"),
                    is_cancel=data.get("isCancel", False)
                )
                session.add(new_order)
                session.commit()
                new_or_updated_orders.append(new_order)
            else:
                # Проверяем, не обновился ли
                if last_change_date_obj > existing_order.last_change_date:
                    existing_order.last_change_date = last_change_date_obj
                    existing_order.is_cancel = data.get("isCancel", False)
                    new_or_updated_orders.append(existing_order)

                # Если supplier_article пустой, обновим
                if not existing_order.supplier_article:
                    existing_order.supplier_article = supplier_art
                    existing_order.full_supplier_article = f"{existing_order.subject} '{supplier_art}'".strip()
                    new_or_updated_orders.append(existing_order)

                # Если techSize пустой, обновим
                if not existing_order.techSize:
                    existing_order.techSize = tech_size
                    new_or_updated_orders.append(existing_order)


            if last_change_date_obj > max_change_date:
                max_change_date = last_change_date_obj

        session.commit()

        # Готовим список словарей
        for o in new_or_updated_orders:
            raw_data = next((x for x in orders_data if x.get("srid") == o.srid), {})
            nm_id = o.nm_id
            # Если нужно, подтягиваем Product
            product = session.query(Product).filter_by(nm_id=nm_id).first()

            all_new_orders_dicts.append({
                "token_id": token_obj.id,
                "srid": o.srid,
                "last_change_date": (o.last_change_date.isoformat() if o.last_change_date else None),
                "date": (o.date.isoformat() if o.date else None),
                "itemName": o.subject,
                "nm_id": o.nm_id,
                "warehouseName": o.warehouse_name,
                "regionName": o.region_name,
                "price_with_disc": raw_data.get("priceWithDisc", 0.0),
                "spp": raw_data.get("spp", 0.0),
                "is_cancel": o.is_cancel,
                "rating": product.rating if product else "N/A",
                "reviews": product.reviews if product else "N/A",
                "image_url": product.image_url if product else None
            })

        # Обновляем глобальный
        LAST_CHECK_DATETIME = max_change_date

    session.close()
    return all_new_orders_dicts
