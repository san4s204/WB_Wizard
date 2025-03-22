import datetime
from db.database import SessionLocal
from db.models import Product
from db.models import ProductSearchRequest, PopularRequest
from sqlalchemy.orm import Session
import time

from core.wildberries_api import get_top_searches_for_nm_id  # наша функция на seller-content.wildberries.ru


def fill_product_search_requests_free():
    """
    1) Берёт все товары (Product).
    2) Для каждого вызывает get_top_searches_for_nm_id(nm_id) (до 10 запросов).
    3) Для каждого phrase ищем frequency в popular_request (по query_text=phrase).
    4) Если frequency >= 200, сохраняем/обновляем в product_search_requests.
    5) Лимит 3 запроса/мин => ставим time.sleep(20) между товарами.

    Старые записи в product_search_requests НЕ удаляем.
    """

    session = SessionLocal()
    products = session.query(Product).all()
    print(f"[INFO] Товаров: {len(products)}")

    count_filled = 0

    for product in products:
        nm_id = product.nm_id
        if not nm_id:
            continue

        print(f"[INFO] Получаем 10 популярных запросов для nm_id={nm_id}...")
        phrases = get_top_searches_for_nm_id(nm_id)  # список словарей

        # чтобы не превысить ~3 запр./мин
        time.sleep(20)

        if not phrases:
            print(f"[WARN] Пусто для nm_id={nm_id}")
            continue

        # phrases ~ [{'position':1, 'phrase':'сумка холодильник', 'count':..., 'dynamic':...}, ...]
        for ph in phrases:
            phrase_text = ph.get("phrase", "").strip().lower()
            if not phrase_text:
                continue

            # Ищем в popular_request
            pop_item = session.query(PopularRequest).filter_by(query_text=phrase_text).first()
            if not pop_item:
                # Если не нашли в popular_request => request_count=0
                freq = 0
            else:
                freq = pop_item.request_count or 0

            # Проверяем, есть ли запись (nm_id, phrase) в product_search_requests
            existing = session.query(ProductSearchRequest).filter_by(
                nm_id=nm_id,
                search_text=phrase_text
            ).first()

            if not existing:
                # Вставляем новую
                new_req = ProductSearchRequest(
                    nm_id=nm_id,
                    search_text=phrase_text,
                    current_freq=freq,
                    last_update=datetime.datetime.utcnow()
                )
                session.add(new_req)
                count_filled += 1
            else:
                # Обновляем частоту / дату
                existing.current_freq = freq
                existing.last_update = datetime.datetime.utcnow()

        session.commit()

    session.close()
    print(f"[INFO] Заполнили/обновили {count_filled} записей в product_search_requests.")

