from db.database import SessionLocal
from db.models import  Product,  DestCity, ProductSearchRequest, ProductPositions
import datetime
import aiohttp
import asyncio
import json
import traceback
# Параллельность
MAX_CONCURRENT = 20
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

CHUNK_SIZE = 5000


async def find_article_in_all_cities(nm_id: int, query_text: str, max_pages=50) -> dict:
    """
    Итерируется по всем записям DestCity, для каждого dest_value (город),
    ищет nm_id по query_text на страницах 1..max_pages (параллельно).
    
    Возвращает словарь: { city_id: (page, pos) или (None, None), ... }
    где city_id - первичный ключ DestCity, 
    page, pos - найденная страница/позиция (или None, None, если не нашли).
    """

    # 1) Загружаем все DestCity из БД
    session = SessionLocal()
    all_cities = session.query(DestCity).all()
    session.close()

    # 2) Готовим результат, туда будем записывать { city.id: (page, pos) }
    results_by_city = {}

    # 3) Для каждого города вызываем ту же логику поиска
    #    Можно делать это последовательно или тоже параллельно (но аккуратно).
    #    Здесь для примера – последовательно, чтобы не плодить слишком много запросов параллельно.
    for city in all_cities:
        city_id = city.id
        dest_value = city.dest

        page, pos = await find_article_in_search_async(nm_id, query_text, dest_value, max_pages=max_pages)
        results_by_city[city_id] = (page, pos)

    return results_by_city

async def find_article_in_search_async(nm_id: int, query_text: str, dest_value: int, max_pages=30) -> tuple:
    """
    Асинхронная версия поиска товара nm_id по query_text + dest_value (город),
    перебирая страницы 1..max_pages параллельно.
    
    Возвращает (page, position) если нашли, иначе (None, None).
    """
    
    
    async def fetch_page(page_num: int) -> tuple:
        """
        Вспомогательная функция:
        - Делает GET на конкретную страницу page_num
        - Возвращает (page_num, position) или (None, None)
        """
        base_url = "https://search.wb.ru/exactmatch/ru/common/v9/search"
        params = {
            "ab_testid": "pers_norm_no_boost",
            "appType": "1",
            "curr": "rub",
            "dest": str(dest_value),
            "hide_dtype": "10",
            "lang": "ru",
            "page": str(page_num),
            "query": query_text,
            "resultset": "catalog",
            "sort": "popular",
            "spp": "30",
            "suppressSpellcheck": "false"
        }

        max_retries = 3
        attempt = 0

        # Лог перед запросом
        while attempt < max_retries:
            attempt += 1
            
            async with aiohttp.ClientSession() as session:
                try:
                    resp = await session.get(base_url, params=params, timeout=30)
                    if resp.status == 429:
                        # Too many requests
                        print(f"[WARN] nm_id={nm_id}, '{query_text}' page={page_num} => 429 Too Many Requests. "
                            f"Попытка {attempt} из {max_retries}. Ждём 120 сек...")
                        await asyncio.sleep(120)
                        # повторяем в этом же цикле (не увеличиваем attempt)
                        continue
                    elif resp.status != 200:
                        print(f"[WARN] nm_id={nm_id}, '{query_text}' page={page_num}, status={resp.status} => прерываем.")
                        return (None, None)

                    text_data = await resp.text()
                    data = json.loads(text_data)
                    products = data.get("data", {}).get("products", [])
                    if not products:
                        return (None, None)
            
                    for idx, product in enumerate(products, start=1):
                        if product.get("id") == nm_id:
                            # Нашли
                            return (page_num, idx)

                    return (None, None)

                except Exception as e:
                    print(f"[ERROR] nm_id={nm_id}, page={page_num}, искл. типа: {type(e).__name__}")
                    print(f"Сообщение исключения: {str(e)}")
                    traceback.print_exc()
                    # При любой ошибке (TimeOut etc) тоже можно повторить
                    # (например, treat like 429?), или просто вернуться None
                    return (None, None)

        # Если дошли сюда => 3 неудачные попытки (3 раза был 429)
        print(f"[ERROR] nm_id={nm_id}, page={page_num} => не удалось получить результат (3x429?).")
        return (None, None)

    # Запускаем задачи параллельно
    tasks = []
    for p in range(1, max_pages + 1):
        task = asyncio.create_task(fetch_page(p))
        tasks.append(task)

    # Ждём результаты
    results = await asyncio.gather(*tasks)

    # results => список [(page or None, pos or None), ...] 
    # извлекаем минимальный page, если есть
    found_pages = [(pg, ps) for (pg, ps) in results if pg is not None]
    if found_pages:
        # ищем с минимальным page
        best = min(found_pages, key=lambda x: x[0])  # (page, pos)
        return best
    else:
        return (None, None)

async def find_article_in_search_with_sema(nm_id: int, query_text: str, dest: int, max_pages=30):
    """
    Обёртка над find_article_in_search_async, чтобы ограничить
    одновременные запросы через семафор.
    """
    async with semaphore:
        return await find_article_in_search_async(nm_id, query_text, dest, max_pages)

def chunk_list(lst, size):
    """
    Генератор: разбивает lst на куски по size.
    """
    for i in range(0, len(lst), size):
        yield lst[i:i+size]

async def update_product_positions_chunked_async():
    """
    Асинхронная функция:
      - Идёт по всем городам (DestCity).
      - Для каждого товара (Product), смотрит запросы в product_search_requests.
      - Чанками обрабатывает (nm_id, search_text) асинхронно,
        вызывает find_article_in_search_async(...) => (page, pos).
      - Записывает результат в product_positions.
    """

    session = SessionLocal()

    # 1) Все города
    cities = session.query(DestCity).all()
    # 2) Все товары
    products = session.query(Product).all()

    print(f"[ASYNC] Города: {len(cities)}, Товаров: {len(products)}")

    for city in cities:
        print(f"[ASYNC] Обработка города {city.city} (dest={city.dest})")

        for product in products:
            nm_id = product.nm_id
            token_id = product.token_id
            if not nm_id:
                continue

            # 3) Берём все запросы для данного nm_id из product_search_requests
            #    которые вы заранее сохранили из JAM
            search_reqs = session.query(ProductSearchRequest)\
                .filter_by(nm_id=nm_id)\
                .all()

            if not search_reqs:
                continue

            # Сформируем список [(query_text, current_freq), ...]
            all_queries = [(sr.search_text, sr.current_freq) for sr in search_reqs]

            # 4) chunk'ами обрабатываем
            for chunk in chunk_list(all_queries, CHUNK_SIZE):
                tasks = []
                for (qtext, freq) in chunk:
                    tasks.append(find_article_in_search_with_sema(
                        nm_id, qtext, city.dest, max_pages=30
                    ))

                # Запускаем асинхронно
                results = await asyncio.gather(*tasks)

                # Сохраняем в product_positions
                for i, (page, pos) in enumerate(results):
                    query_text, req_freq = chunk[i]
                    
                    # записываем (page, pos) в product_positions
                    new_pp = ProductPositions(
                        nm_id = nm_id,
                        token_id=token_id,
                        city_id = city.id,
                        query_text = query_text,
                        request_count = req_freq,
                        page = page,
                        position = pos,
                        check_dt = datetime.datetime.utcnow()
                    )
                    session.add(new_pp)

                session.commit()
    
    session.close()
    print("[ASYNC] Готово! Позиции обновлены .")


