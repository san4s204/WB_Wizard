import requests
import aiohttp
from config import WB_API_KEY
import datetime
from typing import List, Dict, Any


BASE_URL = "https://statistics-api.wildberries.ru/api"
SUPPLIES_BASE_URL = "https://supplies-api.wildberries.ru/api"


SELLER_ANALYTICS_URL = "https://seller-analytics-api.wildberries.ru"

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

def get_search_texts_jam(
    nm_ids: List[int],
    current_period: Dict[str, Any],
    top_order_by: str = "orders",
    order_field: str = "avgPosition",
    order_mode: str = "asc",
    limit: int = 30,) -> List[Dict[str, Any]]:
    """
    Делает POST на https://seller-analytics-api.wildberries.ru/api/v2/search-report/product/search-texts
    Получает список поисковых запросов.

    Параметры:
      nm_ids: список артикулов (макс. 50)
      current_period, past_period:
        форматы вида {
          "dateFrom": "2023-08-01",
          "dateTo":   "2023-08-15"
          }
        или {"days": 7} (зависит от спецификации)
      top_order_by:
        одно из ["openCard", "addToCart", "openToCart", "orders", "cartToOrder"]
      order_field:
        одно из ["avgPosition","openCard","addToCart","openToCart","orders","cartToOrder","visibility","minPrice","maxPrice"]
      order_mode: "asc" или "desc"
      limit: 1..30 (кол-во поисковых запросов по товару, которое вернётся)

    Возвращает список словарей, к примеру:
    [
      {
        "text": "...",
        "nmId": 123456,
        "frequency": {"current": 5, "dynamics": 50},
        ...
      },
      ...
    ]

    Пример current_period/past_period:
      current_period = {"dateFrom": "2023-08-01", "dateTo": "2023-08-15"}
      past_period = {"dateFrom": "2023-07-17", "dateTo": "2023-07-31"}
      или
      current_period = {"days": 14}
      past_period = {"days": 14}
    """
    url = f"{SELLER_ANALYTICS_URL}/api/v2/search-report/product/search-texts"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": WB_API_KEY  # токен из подписки
    }

    body = {
        "currentPeriod": current_period,
        "nmIds": nm_ids,  # список артикулов
        "topOrderBy": top_order_by,
        "orderBy": {
            "field": order_field,
            "mode": order_mode
        },
        "limit": limit
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        data = response.json()
        # Обычно структура: {"data": {"items": [...], ...}}
        # Вернём "items" как список
        items = data.get("data", {}).get("items", [])
        return items

    except requests.RequestException as e:
        print(f"[get_search_texts_jam] Ошибка при запросе: {e}")
        print(f"Status code: {response.status_code}")
        print(f"Response text: {response.text}")
        return []
    
def get_top_searches_for_nm_id(nm_id: int) -> list[dict]:
    """
    Возвращает список (до 10) популярных запросов для данного nm_id 
    через URL:
      https://seller-content.wildberries.ru/ns/analytics-api/content-analytics/api/v2/product/search-texts?nm_id=...
    Пример ответа:
      {
        "data": {
          "phrases": [
            {
              "position": 1,
              "phrase": "сумка холодильник",
              "count": 11,
              "dynamic": 11
            }
          ]
        }
      }
    Возвращает список dict {"position":..., "phrase":..., "count":..., "dynamic":...}.
    """

    url = f"https://seller-content.wildberries.ru/ns/analytics-api/content-analytics/api/v2/product/search-texts?nm_id={nm_id}"
    headers = {
        "Accept": "application/json",
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json',
        'cookie': '_wbauid=9786480411727682056; ___wbu=062e554c-918d-4b90-aed9-7ecd21e06b87.1727682056; wbx-validation-key=8264e3bd-f157-4671-866d-5435893ac871; cfidsw-wb=; external-locale=ru; x-supplier-id-external=a59b225e-1830-4679-9523-4f92170eae3f; __zzatw-wb=MDA0dC0cTHtmcDhhDHEWTT17CT4VHThHKHIzd2UuPW4jX0xaIzVRP0FaW1Q4NmdBEXUmCQg3LGBwVxlRExpceEdXeiwcGHpvK1UJFGJCQmllbQwtUlFRS19/Dg4/aU5ZQ11wS3E6EmBWGB5CWgtMeFtLKRZHGzJhXkZpdRVYCkFjQ0Zxd1xEIyVje2IldVxUCCtMR3pvWE8KCxhEcl9vG3siXyoIJGM1Xz9EaVhTMCpYQXt1J3Z+KmUzPGwgZkpdJ0lXVggqGw1pN2wXPHVlLwkxLGJ5MVIvE0tsP0caRFpbQDsyVghDQE1HFF9BWncyUlFRS2EQR0lrZU5TQixmG3EVTQgNND1aciIPWzklWAgSPwsmIBR+bidXDQ1kREZxbxt/Nl0cOWMRCxl+OmNdRkc3FSR7dSYKCTU3YnAvTCB7SykWRxsyYV5GaXUVCAwUFT9DcjAmPG0gX0RdJUpeSgoqGxR0b1lYCQxiPXYmMCxxVxlRDxZhDhYYRRcje0I3Yhk4QhgvPV8/YngiD2lIYCJKWFEJKxwRd24jS3FPLH12X30beylOIA0lVBMhP05yRG0u1A==; WBTokenV3=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Mzg2NTE3NTMsInZlcnNpb24iOjIsInVzZXIiOiI1Mjk2MDUxNCIsInNoYXJkX2tleSI6IjE5IiwiY2xpZW50X2lkIjoic2VsbGVyLXBvcnRhbCIsInNlc3Npb25faWQiOiI5M2Y4NjU0NGM5Zjg0ZDk2Yjc3NzZjZjM0ZTAzMGU3YSIsInVzZXJfcmVnaXN0cmF0aW9uX2R0IjoxNjkwMTc2NzY3LCJ2YWxpZGF0aW9uX2tleSI6IjUwMDk3MWUyZjhmYTUwM2M5ZjU3YTBiZGU5YmU1MzQwNGEyYjJlYjgxMGQ0YjNjMGMwY2U4NWY4ZmEwNTM1ZmUifQ.J8_hICp4fawk0rrDY-GQOJDEaI_ZUZIYSH7gIogE1aNJjmK4pFEwBgmFozxt4grjoGX0kSp8AtcQdVW8LpX4gqSgV1lupieke3rLIaJNSlfruQXzPnTCpaqFn5w_wVc2bejhWDOQyzCOjy5SOdxSh9Y9O8vaC3TTE-ITgWgJ51StNwAtd0q4VO2ap3cAKO6BsAO-Gxqh4zzKBxER0nWI9XRwziMx3HcuB9PpQWP37ghNXblM_ULsVx2I-Y6lRGnnF071KDMwearno-lMqDCY3i_554TCizUhZgzBDhG_C5TMo7GNPp1_W67_9JR2yrU9KQ3KYrV-TTqQaXSBuF6CFg',
        'origin': 'https://seller.wildberries.ru',
        'priority': 'u=1, i',
        'referer': 'https://seller.wildberries.ru/',
        'sec-ch-ua': '"Opera GX";v="116", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        "Authorization": WB_API_KEY,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0 (Edition Yx GX 03)'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # data["data"]["phrases"]
        phrases = data.get("data", {}).get("phrases", [])
        return phrases  # список словарей
    except requests.RequestException as e:
        print(f"[get_top_searches_for_nm_id] Ошибка: {e}")
        return []