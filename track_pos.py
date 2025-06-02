import asyncio
import aiohttp
import datetime
from typing import Dict, Any
from db.database import SessionLocal
from db.models import PopularRequest, TrackedPosition

API_BASE_URL = "https://search.wb.ru/exactmatch/ru/common/v9/search"
MAX_PAGES = 30
SEMAPHORE_LIMIT = 10  # Параллелим до 3 запросов на WB одновременно

async def fetch_page(
    session_http: aiohttp.ClientSession,
    q_text: str,
    page_num: int,
    request_counter: Dict[str, int],
    page_progress: Dict[str, int],
    sem: asyncio.Semaphore
) -> Dict[str, Any]:
    """
    Запрашивает WB по странице page_num для поискового запроса q_text.
    Возвращает словарь:
      {
        'page': page_num,
        'products': [...],
        'error': str | None
      }

    - request_counter: словарь-хранилище глобального счётчика запросов (для паузы каждые 200k).
    - page_progress: словарь { 'pages_done': int }, для отображения общего прогресса (по страницам).
    - total_pages: общее количество страниц, которые нужно отработать (для %).
    - sem: asyncio.Semaphore(...) чтобы ограничить параллелизм (до 3).
    """

    params = {
        "ab_testid": "rel_promo_masks_p50",
        "appType": "1",
        "curr": "rub",
        "dest": "-1785054",
        "lang": "ru",
        "page": page_num,
        "query": q_text,
        "resultset": "catalog",
        "sort": "popular",
        "spp": "30",
        "suppressSpellcheck": "false",
        "uclusters": "5",                                                                                                       
        "uiv": "0",
        "uv": "AQEAAQIACLpVufFF5jwMPnxB..."  # Пример
    }

    async with sem:  # не более 3 корутин одновременно
        try:
            # Проверка на паузу каждые 200k запросов
            if request_counter["count"] > 0 and request_counter["count"] % 200_000 == 0:
                print("Достигнуто 200k запросов, делаем паузу на 15 минут...")
                await asyncio.sleep(15 * 60)

            request_counter["count"] += 1
            async with session_http.get(API_BASE_URL, params=params, timeout=10) as resp:
                if resp.status != 200:
                    msg = f"[page={page_num}] Статус {resp.status}, пропускаем."
                    print(msg)
                    # Увеличим счётчик страниц, даже если ошибка
                    page_progress["pages_done"] += 1
                    return {"page": page_num, "products": [], "error": msg}

                # Игнорируем Content-Type text/plain и парсим как JSON
                data = await resp.json(content_type=None)
                products = data.get("data", {}).get("products", [])

                # Увеличиваем счётчик обработанных страниц
                page_progress["pages_done"] += 1

                return {"page": page_num, "products": products, "error": None}

        except Exception as exc:
            msg = f"[page={page_num}] Ошибка запроса: {exc}"
            print(msg)
            page_progress["pages_done"] += 1
            return {"page": page_num, "products": [], "error": msg}


async def track_positions():
    """
    Асинхронно:
      - Перебирает popular_request
      - Для каждого запроса q_text делает до 30 запросов (по страницам) ПАРАЛЛЕЛЬНО (до 3 одновременно)
      - Сохраняет позиции в TrackedPosition (page, position).
      - Показывает прогресс и по запросам, и по страницам.
    """

    db_sess = SessionLocal()
    all_requests = db_sess.query(PopularRequest).all()
    total_requests = len(all_requests)
    if total_requests == 0:
        print("Нет запросов в popular_request, ничего не трекаем.")
        db_sess.close()
        return

    print(f"Найдено {total_requests} запросов для трекинга.")
    
    # Общий счётчик запросов, чтобы делать паузу каждые 200k
    request_counter = {"count": 0}
    # Прогресс по страницам
    total_pages = total_requests * MAX_PAGES
    page_progress = {"pages_done": 0}

    async with aiohttp.ClientSession() as session_http:
        # Идём по всем popular_request
        for idx_request, popular_req in enumerate(all_requests, start=5262):
            q_id = popular_req.id
            q_text = popular_req.query_text

            # Прогресс по запросам
            percent_requests = (idx_request / total_requests) * 100
            print(f"\n[{idx_request}/{total_requests}] ({percent_requests:.1f}%) => query_id={q_id}, text='{q_text}'")

            sem = asyncio.Semaphore(SEMAPHORE_LIMIT)

            # Создаём таски на все страницы (1..MAX_PAGES)
            tasks = []
            for page_num in range(1, MAX_PAGES + 1):
                coro = fetch_page(session_http, q_text, page_num,
                                  request_counter, page_progress, total_pages, sem)
                tasks.append(asyncio.create_task(coro))

            # Запускаем все страницы для данного запроса параллельно
            results = await asyncio.gather(*tasks)

            # Записываем позиции в БД
            need_commit = False
            for res in results:
                page = res["page"]
                error = res["error"]
                products = res["products"]

                # Если ошибка, пропускаем
                if error:
                    continue

                # Пустая страница => вряд ли есть товары
                if not products:
                    continue

                for pos_idx, product in enumerate(products, start=1):
                    pid = product.get("id")
                    if pid is None:
                        continue
                    db_sess.add(TrackedPosition(
                        query_id=q_id,
                        product_id=pid,
                        page=page,
                        position=pos_idx,
                        check_dt=datetime.datetime.utcnow()
                    ))
                    need_commit = True

            if need_commit:
                db_sess.commit()

    db_sess.close()
    print("\nТрекинг позиций завершён.")


# Пример одиночного запуска
if __name__ == "__main__":
    asyncio.run(track_positions())
