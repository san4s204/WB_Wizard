import requests
import aiohttp
from config import WB_API_KEY
import datetime
from typing import List, Dict, Any
import traceback
import json
import re

BASE_URL = "https://statistics-api.wildberries.ru/api"
SUPPLIES_BASE_URL = "https://supplies-api.wildberries.ru/api"
BASE_CARDS_URL = "https://card.wb.ru/cards/v2/detail"
SELLER_ANALYTICS_URL = "https://seller-analytics-api.wildberries.ru"
CARD_BASE_URL = "https://card.wb.ru/cards/v2/detail"
COMMON_BASE = "https://common-api.wildberries.ru/api/v1/tariffs"

async def get_orders(date_from: str, user_token:str, flag: int = 0):
    """
    Запрашивает заказы, у которых:
      - lastChangeDate >= dateFrom (если flag=0)
      - или все заказы с датой, равной (или больше) dateFrom (если flag=1)
    Format date_from: "2023-12-31T12:34:56"

    Возвращает список (list) заказов в JSON-формате.

    Документация:
    https://statistics-api.wildberries.ru/api/v5/supplier/reportDetailByPeriod
    https://openapi.wildberries.ru/statistics/api/ru/
    """
    headers = {
        "Authorization": user_token,
    }
    params = {
        "dateFrom": date_from,
        "flag": flag
        # При необходимости можно добавить другие параметры, если нужны
    }

    url = f"{BASE_URL}/v1/supplier/orders"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=30) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception as e:
        print(f"Ошибка при запросе к Wildberries /orders: {e}")
        return []

async def get_report_detail_by_period(
    date_from: str, 
    date_to: str, 
    user_token:str,
    rrdid: int = 0, 
    limit: int = 100000,
):
    """
    date_from, date_to: строки в формате RFC3339 (UTC+3 в доке).
    rrdid: с чего начинаем (0 - первый запрос).
    limit: макс кол-во строк за один вызов.
    
    Возвращаем JSON-массив (list) или пустой список, если ничего нет.
    """
    headers = {"Authorization": user_token}
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
        "rrdid": rrdid,
        "limit": limit
    }
    url = f"{BASE_URL}/v5/supplier/reportDetailByPeriod"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=30) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception as e:
        print(f"Ошибка при запросе к Wildberries /report_detail: {e}")
        return []

async def fetch_full_report(date_from: str, date_to: str, user_token: str) -> list[dict]:
    """
    Выгружает все строки отчёта за период [date_from, date_to],
    используя постраничный (построчный) подход по rrdid.
    Возвращает общий список (list) со всеми записями.
    """
    all_data = []
    current_rrdid = 0
    limit = 100000

    while True:
        data_part = await get_report_detail_by_period(date_from, date_to, rrdid=current_rrdid, limit=limit, user_token=user_token)
        if not data_part:
            # пусто => всё, выходим
            break

        all_data.extend(data_part)
        
        # rrdid последнего
        last_rrdid = data_part[-1]["rrd_id"]  # по документации "rrd_id" = rrdid
        if len(data_part) < limit:
            # значит, выкачали последние строки
            break
        else:
            # продолжаем
            current_rrdid = last_rrdid
    
    return all_data

async def get_sales(date_from: str, user_token:str, flag: int = 0) -> list[dict]:
    """
    Запрашивает выкупы, у которых:
      - lastChangeDate >= dateFrom (если flag=0)
      - или все продажи с датой >= dateFrom (если flag=1)
    Format date_from: "YYYY-MM-DDTHH:MM:SS"
    Возвращает список (list) продаж.
    https://statistics-api.wildberries.ru/api/v1/supplier/sales
    """
    headers = {"Authorization": user_token}
    params = {
        "dateFrom": date_from,
        "flag": flag
    }
    url = f"{BASE_URL}/v1/supplier/sales"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=30) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception as e:
        print(f"Ошибка при запросе к Wildberries /sales: {e}")
        return []

async def get_stocks(date_from: str, user_token:str) -> list[dict]:
    """
    Запрашивает остатки на складе на указанную дату.
    Возвращает список (list) остатков.
    https://statistics-api.wildberries.ru/api/v1/supplier/stocks
    """
    headers = {"Authorization": user_token}
    params = {
        "dateFrom": date_from,
    }
    url = f"{BASE_URL}/v1/supplier/stocks"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=30) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception as e:
        print(f"Ошибка при запросе к Wildberries /stocks: {e}")
        return []

async def get_incomes(date_from: str, user_token: str) -> list[dict]:
    """
    Запрашивает информацию о поставках (Incomes) с указанной даты date_from (формат '2025-01-01').
    Возвращает список (list) из словарей с полями:
      incomeId, number, date, lastChangeDate, supplierArticle, techSize, barcode,
      quantity, totalPrice, dateClose, warehouseName, nmId, status.
    Документация: https://statistics-api.wildberries.ru/api/v1/supplier/incomes
    """
    headers = {"Authorization": user_token}
    params = {"dateFrom": date_from}
    url = f"{BASE_URL}/v1/supplier/incomes"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=30) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception as e:
        print(f"Ошибка при запросе к Wildberries /incomes: {e}")
        return []

def _parse_cost(raw) -> float | None:
    """
    Безопасно парсим цену:
    - пропускаем '-', '—', пустые строки, None
    - чистим пробелы/неразрывные пробелы, валюты/символы
    - меняем ',' -> '.'
    - берём первое число из строки
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    s = str(raw).strip()
    if s in {"", "-", "—", "N/A", "NaN", "нет", "нет данных"}:
        return None

    s = s.replace("\u00a0", " ")      # NBSP -> space
    s = s.replace(" ", "")
    s = s.replace(",", ".")
    # вытащим первое валидное число
    m = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None

async def get_tariffs_for_date(user_token: str, kind: str = "box",  dt: datetime.date | str | None = None) -> list[dict]:
    headers = {"Authorization": user_token}

    if dt is None:
        dt = datetime.date.today()
    if isinstance(dt, datetime.date):
        dt = dt.isoformat()

    url = f"{COMMON_BASE}/{kind}"
    params = {"date": dt}
    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(url, headers=headers, params=params) as r:
            r.raise_for_status()
            full = await r.json()

    # аккуратнее достаём список складов
    data = full.get("response", {}).get("data", {})
    wl = data.get("warehouseList", []) or []

    cleaned: list[dict] = []
    for w in wl:
        if kind == "box":
            raw_cost = w.get("boxDeliveryBase")
            b_type_id, b_type_name = 2, "Короба"
        else:
            raw_cost = w.get("palletDeliveryValueBase")
            b_type_id, b_type_name = 6, "Паллеты"

        cost = _parse_cost(raw_cost)
        if cost is None:
            # можно залогировать, если нужно:
            # logging.debug(f"skip tariff: kind={kind}, wh={w.get('warehouseName')}, raw={raw_cost!r}")
            continue

        cleaned.append({
            "warehouseName": w.get("warehouseName"),
            "boxTypeId"    : b_type_id,
            "boxTypeName"  : b_type_name,
            "tariff"       : cost,
        })
    return cleaned

async def get_acceptance_coefficients(user_token: str) -> list[dict]:
    """
    GET /api/v1/acceptance/coefficients
    Возвращает список коэффициентов приёмки на ближайшие 14 дней для всех складов.
    Документация: https://supplies-api.wildberries.ru/api/v1/acceptance/coefficients

    Пример ответа:
    [
      {
        "date": "2025-03-12T00:00:00Z",
        "coefficient": -1,
        "warehouseID": 158311,
        "warehouseName": "СЦ Пятигорск",
        "allowUnload": true,
        "boxTypeName": "Короба",
        "boxTypeID": 2,
        ...
      },
      ...
    ]
    """
    headers = {
        "Authorization": user_token
    }
    url = f"{SUPPLIES_BASE_URL}/v1/acceptance/coefficients"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception as e:
        print(f"Ошибка при запросе к Wildberries /accept_coef: {e}")
        return []

def get_seller_info(user_token:str) -> dict:
    """
    Делает GET-запрос к https://common-api.wildberries.ru/api/v1/seller-info
    Возвращает словарь с информацией о магазине { "name": "...", "sid": "...", tradeMark: "..." }
    """
    url = "https://common-api.wildberries.ru/api/v1/seller-info"
    headers = {
        "Authorization": user_token,  # Если WB требует токен в заголовке (пример)
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers, timeout=5)
    response.raise_for_status()
    return response.json()

async def get_promo_text_card(nm_id: int) -> str:
    """
    Делает запрос:
    GET https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1785058&hide_dtype=13&spp=30&ab_testing=false&lang=ru&nm={nm_id}
    
    Возвращает promoTextCard (строку) или пустую строку, если promoTextCard не найден.
    """
    params = {
        "appType": "1",
        "curr": "rub",
        "dest": "-1785058",       # обычно -1785058 или ваше
        "hide_dtype": "13",
        "spp": "30",
        "ab_testing": "false",
        "lang": "ru",
        "nm": str(nm_id)
    }

    # headers — минимально нужные. Если WB не требует капчи/других заголовков,
    # можно оставить упрощённый вариант:
    headers = {
        "accept": "*/*",
        "user-agent": "Mozilla/5.0 (compatible; WBWizardBot/1.0; +https://example.com)"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_CARDS_URL, headers=headers, params=params, timeout=20) as resp:
                if resp.status != 200:
                    print(f"[get_promo_text_card] nm_id={nm_id}, status={resp.status}")
                    return ""
                text_data = await resp.text()
                data = json.loads(text_data)
                products = data.get("data", {}).get("products", [])
                if not products:
                    return ""
                # Берём первую запись
                product = products[0]
                promo_text = product.get("promoTextCard", "")
                return promo_text or ""
    except Exception as e:
        print(f"[get_promo_text_card] nm_id={nm_id}, исключение: {type(e).__name__} => {e}")
        traceback.print_exc()
        return ""

async def get_search_queries_mayak(nm_id: int) -> list[dict]:
    """
    Делает запрос к сервису https://app.mayak.bz/api/v1/wb/products/{nm_id}/word_ranks,
    который (по вашим данным) возвращает поисковые запросы по артикулу.
    
    Возвращает list[dict], где каждый dict - информация о рангах.
    
    Пример URL:
      https://app.mayak.bz/api/v1/wb/products/198362333/word_ranks
    """

    url = f"https://app.mayak.bz/api/v1/wb/products/{nm_id}/word_ranks"

    # Если нужна cookie/другие заголовки, можно оставить:
    headers = {
        # Ниже cookie из вашего запроса; в реальном коде лучше или убрать,
        # или обновлять при необходимости, т.к. cookie может протухнуть.
        'Cookie': '_wb_session=aYdd6fMGWcprPpg90AmXycZhpUuopR7I4bkL8Xh9u7cf%2BgpjdNMg%2FRYiOXQNUcCO5Xt9MNWG3vWeqS14NfGxpHtInACRweIgRdvXq8Ye7RHz%2BKFMAYtaM8qywjtL54pqUrPC%2Bi6evAo9u3O%2B8qj9UnLBlDDMjBLGdnN88MD99UPo8zTQqx9ahggFGuJsd9IZv0618JjOadHD7SL2cCwoZMVJEMvsE8texj59eFp8bNn%2BSBkVRug7DticaBUuhFRx%2F6t3jVrZIOKaoCl8%2FgdfCNMfJJF1spqk5N1sMMPLe9M%2Fu1oc4nochJoXMA9InxjXCjyzxheJ5%2F3IhxPBxOjLef80E8oi%2B3Z4xktJhuL%2FFgqiH%2FMdrDVWSz65Xv9ERddFZFAnEyKcHvLdcPi0fL45yHZD1PECEx3YLPaNQoeZxcsEKeR461zti1rDU46OCSA8eUdC9WVCzzCh%2BE3XsWvZpX2XVxBbNQB%2BagKzdZhR1HvTtqmuxktaqp43QbhN3x4PkTV%2Fr9rJuUHYOcyTCCig2YPqbY%2BAwrK%2F9HS70%2FikvkCmOmWWJD53H4tLy0IUv3V3udBof2XWmfTaOXmZyS%2FibziwIw9IYVVhoZRkdnhJoSqFilAZrWvWfWIXYEuQdCd36rTJvCbBSHmFhILH4Hltn3fp2aKfzgdtxZM59ge%2FTg%3D%3D--vjGmBTcg6z3eLabQ--Ca9SvxpwJvBXaWblijc1uA%3D%3D', 
        'accept': '*/*',
        'user-agent': 'Mozilla/5.0 (compatible; WBWizardBot/1.0; +https://example.com)'
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as resp:
                if resp.status != 200:
                    print(f"[get_search_queries_mayak] nm_id={nm_id}, status={resp.status}")
                    return []
                text_data = await resp.text()
                data = json.loads(text_data)
                # Предположим, API возвращает что-то вроде {"data": {...}}
                # Надо смотреть реальный формат. Если "word_ranks" - это ключ, ищите data["word_ranks"] и т.д.
                # Ниже просто пример, как вернуть data
                return data  # Или data.get("word_ranks", [])

    except Exception as e:
        print(f"[get_search_queries_mayak] nm_id={nm_id}, исключение: {type(e).__name__} => {e}")
        traceback.print_exc()
        return []

async def get_rating_and_feedbacks(nm_id: int,
                                   dest: int = -1257786,
                                   spp: int = 30,
                                   app_type: int = 1) -> tuple[float | None, int | None]:
    """
    Запрашивает карточку товара и возвращает (review_rating, feedbacks).

    ▸ `nm_id`      – артикул WB  
    ▸ `dest`       – регион (по-умолчанию = Москва)  
    ▸ `spp` / `app_type` – стандартные параметры карточки.

    Возвращает кортеж:
        (review_rating: float | None, feedbacks: int | None)
    """
    params = {
        "appType":  app_type,
        "curr":     "rub",
        "dest":     dest,
        "hide_dtype": 13,
        "spp":      spp,
        "nm":       nm_id
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CARD_BASE_URL, params=params, timeout=15) as resp:
                resp.raise_for_status()
                data = await resp.json()

        product = data.get("data", {}).get("products", [{}])[0]
        rating   = product.get("reviewRating")        # float 4.6
        reviews  = product.get("feedbacks")           # int   29331
        return rating, reviews

    except Exception as exc:
        print(f"[get_rating_and_feedbacks] nm_id={nm_id} → ошибка: {exc}")
        return None, None
