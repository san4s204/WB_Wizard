import datetime
from db.database import SessionLocal
from db.models import Product
from db.models import ProductSearchRequest
import asyncio

from core.wildberries_api import get_search_queries_mayak  # наша функция на seller-content.wildberries.ru


async def fill_product_search_requests_async():
    """
    Асинхронная версия:
    1) Берём все товары (Product).
    2) Для каждого nm_id вызываем (асинхронно) get_search_queries_mayak(nm_id).
    3) В ответе берем "word_ranks": [{ "word":..., "wb_frequency":..., ...}, ...].
    4) Записываем/обновляем в product_search_requests.
    5) Чтобы не превышать лимит ~3 запроса/мин, делаем await asyncio.sleep(20) между товарами.
    """

    session = SessionLocal()
    products = session.query(Product).all()
    print(f"[INFO] Товаров: {len(products)}")

    count_filled = 0

    for product in products:
        nm_id = product.nm_id
        if not nm_id:
            continue

        print(f"[INFO] Получаем поисковые запросы для nm_id={nm_id} через mayak.bz...")

        # Асинхронный запрос
        response_data = await get_search_queries_mayak(nm_id)
        # Ожидаемый формат ответа: { "word_ranks": [ { "word":"...", "wb_frequency":..., ...}, ...] }
        if not response_data or "word_ranks" not in response_data:
            print(f"[WARN] Пусто или нет word_ranks для nm_id={nm_id}")
            # Подождём 20 сек перед следующим товаром
            await asyncio.sleep(2)
            continue

        word_ranks = response_data["word_ranks"]

        # Сохраняем/обновляем в product_search_requests
        for wr in word_ranks:
            phrase_text = wr.get("word", "").strip().lower()
            freq = wr.get("wb_frequency", 0)

            if freq < 20:
                continue

            if not phrase_text:
                continue

            existing = session.query(ProductSearchRequest).filter_by(
                nm_id=nm_id,
                search_text=phrase_text
            ).first()
            if not existing:
                new_req = ProductSearchRequest(
                    nm_id=nm_id,
                    search_text=phrase_text,
                    current_freq=freq,
                    last_update=datetime.datetime.utcnow()
                )
                session.add(new_req)
                count_filled += 1
            else:
                existing.current_freq = freq
                existing.last_update = datetime.datetime.utcnow()

        session.commit()

        # Пауза 20 сек между товарами
        await asyncio.sleep(2)

    session.close()
    print(f"[INFO] Заполнили/обновили {count_filled} записей в product_search_requests.")

