import datetime
from db.database import SessionLocal
from db.models import Sale, Product, Token
from sqlalchemy.orm import Session
from utils.logger import logger
from core.wildberries_api import get_sales

LAST_CHECK_DATETIME_SALES = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
PERIOD_DAYS = 90
async def check_new_sales() -> list[dict]:
    """
    1) Берёт все токены (tokens),
    2) Для каждого токена делает запрос к WB /sales,
    3) Сохраняет/обновляет записи в таблице Sales (sale.token_id=...),
    4) Возвращает общий список новых/обновлённых выкупов в формате [{"token_id":..., "sale_id":..., ...}, ...].
    """
    logger.info("Запуск проверки новых/обновлённых выкупов (sales)...")
    global LAST_CHECK_DATETIME_SALES

    session: Session = SessionLocal()

    tokens = session.query(Token).all()

    date_from_str = (datetime.datetime.now() - datetime.timedelta(days=PERIOD_DAYS)).isoformat()
    logger.debug(f"date_from = {date_from_str}")

    all_new_sales_list = []

    for token_obj in tokens:
        token_value = token_obj.token_value

        # Запрашиваем /sales c учётом date_from_str
        sales_data = await get_sales(date_from_str, token_value, flag=0) 
        # get_sales(token_value, date_from: str, flag=0) -> ваш вариант

        logger.info(f"Token_id={token_obj.id}, получено {len(sales_data)} выкупов.")

        if not sales_data:
            continue

        # Тут можно сделать отдельный max_change_date, если хотим
        # (но тогда хранить LAST_CHECK_DATETIME_SALES на токен)
        # Для упрощения оставим глобальный
        max_change_date = LAST_CHECK_DATETIME_SALES

        new_or_updated_sales = []

        for data in sales_data:
            sale_id = data.get("saleID") or data.get("saleId")
            last_change_date_str = data.get("lastChangeDate")
            if not sale_id or not last_change_date_str:
                logger.debug(f"Пропускаем некорректную запись {data}")
                continue

            # Парсим дату
            try:
                dt = datetime.datetime.fromisoformat(last_change_date_str)
                dt_utc = dt.astimezone(datetime.timezone.utc)
                last_change_date_obj = dt_utc.replace(tzinfo=None)
            except ValueError:
                last_change_date_obj = LAST_CHECK_DATETIME_SALES

            existing_sale = (
                session.query(Sale)
                .filter_by(sale_id=sale_id, token_id=token_obj.id)
                .first()
            )

            if not existing_sale:
                # Новый выкуп
                logger.debug(f"Новый выкуп sale_id={sale_id} для token_id={token_obj.id}.")
                subject = data.get("subject", "")
                sale_date_str = data.get("date") or ""
                sale_date = None
                if sale_date_str:
                    # убираем "Z" или парсим c ISO
                    sale_date_str = sale_date_str.replace("Z", "")
                    try:
                        sale_date = datetime.datetime.fromisoformat(sale_date_str)
                    except:
                        pass

                new_sale = Sale(
                    token_id=token_obj.id,
                    sale_id=sale_id,
                    last_change_date=last_change_date_obj,
                    date=sale_date,
                    warehouse_name=data.get("warehouseName"),
                    region_name=data.get("regionName"),
                    subject=subject,
                    nm_id=data.get("nmId"),
                    brand=data.get("brand"),
                    price_with_disc=data.get("priceWithDisc"),
                    total_price=data.get("totalPrice"),
                    spp=data.get("spp"),
                    # is_cancel=... (если нужно)
                )
                session.add(new_sale)
                new_or_updated_sales.append(new_sale)
            else:
                # Обновляем, если lastChangeDate стал больше
                if last_change_date_obj > existing_sale.last_change_date:
                    logger.debug(f"Выкуп sale_id={sale_id} обновился.")
                    existing_sale.last_change_date = last_change_date_obj
                    # existing_sale.is_cancel = data.get("isCancel", False) # или иные поля
                    new_or_updated_sales.append(existing_sale)

            if last_change_date_obj > max_change_date:
                max_change_date = last_change_date_obj

        session.commit()

        # Теперь преобразуем new_or_updated_sales -> список словарей
        for s in new_or_updated_sales:
            # Находим сырые данные
            raw_data = next((x for x in sales_data if (x.get("saleID") or x.get("saleId")) == s.sale_id), {})
            nm_id = s.nm_id
            product = session.query(Product).filter_by(nm_id=nm_id).first()

            base_price = float(raw_data.get("priceWithDisc", 0.0))
            spp_value = float(raw_data.get("spp", 0.0))

            all_new_sales_list.append({
                "token_id": token_obj.id,       # <-- ключевой момент
                "sale_id": s.sale_id,
                "last_change_date": s.last_change_date.isoformat() if s.last_change_date else None,
                "date": s.date.isoformat() if s.date else None,
                "itemName": s.subject,
                "nm_id": s.nm_id,
                "warehouseName": s.warehouse_name,
                "regionName": s.region_name,
                "price_with_disc": base_price,
                "spp": spp_value,
                "rating": product.rating if product else "N/A",
                "reviews": product.reviews if product else "N/A",
                "image_url": product.image_url if product else None
            })

        # Обновляем глобальный 
        LAST_CHECK_DATETIME_SALES = max_change_date

    session.close()
    return all_new_sales_list
