import re
import aiohttp
import asyncio
from typing import Union
import requests

def _old_basket_host(vol: int) -> str:
    """Определяем номер корзины по vol (диапазоны актуальны на май-2025)."""
    if   vol <=  143: return "01"
    elif vol <=  287: return "02"
    elif vol <=  431: return "03"
    elif vol <=  719: return "04"
    elif vol <= 1007: return "05"
    elif vol <= 1061: return "06"
    elif vol <= 1115: return "07"
    elif vol <= 1169: return "08"
    elif vol <= 1313: return "09"
    elif vol <= 1601: return "10"
    elif vol <= 1655: return "11"
    elif vol <= 1919: return "12"
    elif vol <= 2045: return "13"
    elif vol <= 2189: return "14"
    elif vol <= 2405: return "15"
    elif vol <= 2621: return "16"
    elif vol <= 2837: return "17"
    elif vol == 4118: return "23"
    else:             return "18"

def old_build_image_url(nm_id: int, size: str = "big", n: int = 1) -> str:
    """Формирование старой версии URL изображения."""
    vol = nm_id // 100_000
    part = nm_id // 1_000
    host = _old_basket_host(vol)
    return f"https://basket-{host}.wbbasket.ru/vol{vol}/part{part}/{nm_id}/images/{size}/{n}.webp"


def new_build_image_url(nm_id: int, size: str = "big", n: int = 1) -> str:
    """Перебор CDN-серверов для нахождения изображения по новой структуре."""
    vol = nm_id // 100_000
    part = nm_id // 1_000
    cdns = list(range(1, 19))  # Список номеров CDN-серверов от 01 до 18
    
    for cdn in cdns:
        url = f"https://nsk-basket-cdn-{cdn:02}.geobasket.ru/vol{vol}/part{part}/{nm_id}/images/{size}/{n}.webp"
        try:
            response = requests.head(url, timeout=3)
            if response.status_code == 200:
                return url
        except requests.RequestException:
            pass
    return None

def check_image_exists(url: str) -> bool:
    """Проверяет существование изображения по указанному URL."""
    try:
        response = requests.head(url, timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False

async def parse_wildberries(ref: Union[str, int]) -> dict:
    # 1. nmId
    nm_id = int(ref) if isinstance(ref, int) else int(re.search(r'(\d{6,})', ref).group(1))
    print (nm_id)

    # 2. запрос карточки
    api_tpl = "https://card.wb.ru/cards/{ver}/detail?appType=1&curr=rub&dest=-1257786&nm={nm}"
    versions = ("v1", "v2", "v3", "v5")           # пробуем по очереди
    timeout  = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(timeout=timeout) as s:
        for ver in versions:
            try:
                async with s.get(api_tpl.format(ver=ver, nm=nm_id)) as r:
                    if r.status != 200:
                        continue
                    data = await r.json()
                    product = data["data"]["products"][0]
                    break      # успех
            except Exception:
                continue       # пробуем следующую версию
        else:
            raise RuntimeError(f"товар {nm_id} card.wb.ru не ответил на всех версиях API")

    # 3. результат
    title       = product.get("name", "")
    supplier_id = product.get("supplierId")
    rating = product.get("reviewRating", 0)
    feedbacks = product.get("feedbacks", 0)
    store_link  = f"https://www.wildberries.ru/seller/{supplier_id}" if supplier_id else ""
    old_image_url = old_build_image_url(nm_id)
    if check_image_exists(old_image_url):
        image_url = old_image_url
    else:
        # Если старая схема не работает, пытаемся найти изображение на новом CDN
        image_url = new_build_image_url(nm_id)

    return {"title": title, "image_url": image_url, "store_link": store_link, "rating": rating, "feedbacks": feedbacks}






# #  # 4. Процент отказов, возвратов и т.д. (просто пример)
#         # Отказы (is_cancel=True)
#         canceled_count = session.query(func.count(Order.id)) \
#             .filter(Order.nm_id == nm_id, Order.is_cancel == True,
#                     Order.date >= date_from, Order.date <= date_to) \
#             .scalar() or 0

#         ws["A8"] = f"Отказов: {canceled_count}"

#         # Возвраты (sale_id like "R%") -- если нужно
#         returns_count = session.query(func.count(Sale.id)) \
#             .filter(Sale.nm_id == nm_id, Sale.sale_id.like("R%"),
#                     Sale.date >= date_from, Sale.date <= date_to) \
#             .scalar() or 0

#         ws["B8"] = f"Возвратов: {returns_count}"

# rating = product.get("reviewRating", 0)
#     feedbacks = product.get("feedbacks", 0)