import datetime
from db.database import SessionLocal
from db.models import Product
from db.models import ProductSearchRequest
from wildberries_api import get_search_texts_jam  # ваш метод с POST запросом
from sqlalchemy.orm import Session

def fill_product_search_requests_3m():
    """
    Проходит по всем товарам (products), 
    вызывает JAM API /api/v2/search-report/product/search-texts 
    на период ~3 месяца (90 дней),
    сохраняет топ-30 поисковых запросов в таблицу product_search_requests.
    """

    session :Session = SessionLocal()

    # 1. Получаем все товары
    all_products = session.query(Product).all()

    # Допустим, 3 месяца назад = 90 дней
    # JAM API позволяет передавать period как {"days": 90} 
    # или dateFrom/dateTo. Для простоты используем days:

    current_period = {"days": 90}
    past_period = {"days": 90}  # В документации сказано, что pastPeriod <= currentPeriod

    # Параметры сортировки
    top_order_by = "orders"       # сортировка по количеству заказов
    order_field = "avgPosition"   # secondary field для сортировки
    order_mode = "asc"            # по возрастанию
    limit = 30                    # возьмём до 30 поисковых запросов

    count_products = 0
    for product in all_products:
        nm_id = product.nm_id
        if not nm_id:
            continue
        
        # 2. Вызываем метод JAM API (по 1 артикулу)
        items = get_search_texts_jam(
            nm_ids=[nm_id],
            current_period=current_period,
            past_period=past_period,
            top_order_by=top_order_by,
            order_field=order_field,
            order_mode=order_mode,
            limit=limit
        )

        # Если ничего не вернули, пропускаем
        if not items:
            continue

        # 3. Удаляем старые записи по nm_id
        session.query(ProductSearchRequest).filter_by(nm_id=nm_id).delete()

        # 4. Создаём новые записи
        for it in items:
            text = it.get("text", "")  # поисковый запрос
            freq = 0
            freq_obj = it.get("frequency", {})
            if isinstance(freq_obj, dict):
                freq = freq_obj.get("current", 0)

            new_rec = ProductSearchRequest(
                nm_id=nm_id,
                search_text=text,
                current_freq=freq
            )
            session.add(new_rec)

        session.commit()
        count_products += 1

    session.close()
    print(f"[fill_product_search_requests_3m] Обработано товаров: {count_products}")

