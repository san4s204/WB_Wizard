import requests
import datetime
from db.database import SessionLocal
from db.models import PopularRequest
import time

def fetch_popular_requests():
    """
    Делает GET-запросы к 
    https://seller-weekly-report.wildberries.ru/ns/trending-searches/suppliers-portal-analytics/api
    и проходит по всем (или N) страницам, собирая text, requestCount.
    Записывает в таблицу popular_request.
    """

    session = SessionLocal()

    # (Опционально) если нужно очистить таблицу перед сбором:
    # deleted_count = session.query(PopularRequest).delete()
    # session.commit()
    # print(f"[fetch_popular_requests] Старые записи удалены: {deleted_count} шт.")

    # Тут нужно подставить нужные headers (cookie, WBToken, и т.д.)
    headers = {
    'accept': '*/*',
    'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'content-type': 'application/json',
    'cookie': '_wbauid=9786480411727682056; ___wbu=062e554c-918d-4b90-aed9-7ecd21e06b87.1727682056; wbx-validation-key=8264e3bd-f157-4671-866d-5435893ac871; cfidsw-wb=; external-locale=ru; x-supplier-id-external=a59b225e-1830-4679-9523-4f92170eae3f; __zzatw-wb=MDA0dC0cTHtmcDhhDHEWTT17CT4VHThHKHIzd2UuPW4jX0xaIzVRP0FaW1Q4NmdBEXUmCQg3LGBwVxlRExpceEdXeiwcGHpvK1UJFGJCQmllbQwtUlFRS19/Dg4/aU5ZQ11wS3E6EmBWGB5CWgtMeFtLKRZHGzJhXkZpdRVYCkFjQ0Zxd1xEIyVje2IldVxUCCtMR3pvWE8KCxhEcl9vG3siXyoIJGM1Xz9EaVhTMCpYQXt1J3Z+KmUzPGwgZkpdJ0lXVggqGw1pN2wXPHVlLwkxLGJ5MVIvE0tsP0caRFpbQDsyVghDQE1HFF9BWncyUlFRS2EQR0lrZU5TQixmG3EVTQgNND1aciIPWzklWAgSPwsmIBR+bidXDQ1kREZxbxt/Nl0cOWMRCxl+OmNdRkc3FSR7dSYKCTU3YnAvTCB7SykWRxsyYV5GaXUVCAwUFT9DcjAmPG0gX0RdJUpeSgoqGxR0b1lYCQxiPXYmMCxxVxlRDxZhDhYYRRcje0I3Yhk4QhgvPV8/YngiD2lIYCJKWFEJKxwRd24jS3FPLH12X30beylOIA0lVBMhP05yRG0u1A==; captchaid=1739259203|bdbd7e603da447dea668527b3791c523|442JEp|4j22ypf5rBz4c5LeP4sBSClk1l6o1MUZy8vllGwDBSf; WBTokenV3=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3Mzg2NTE3NTMsInZlcnNpb24iOjIsInVzZXIiOiI1Mjk2MDUxNCIsInNoYXJkX2tleSI6IjE5IiwiY2xpZW50X2lkIjoic2VsbGVyLXBvcnRhbCIsInNlc3Npb25faWQiOiI5M2Y4NjU0NGM5Zjg0ZDk2Yjc3NzZjZjM0ZTAzMGU3YSIsInVzZXJfcmVnaXN0cmF0aW9uX2R0IjoxNjkwMTc2NzY3LCJ2YWxpZGF0aW9uX2tleSI6IjUwMDk3MWUyZjhmYTUwM2M5ZjU3YTBiZGU5YmU1MzQwNGEyYjJlYjgxMGQ0YjNjMGMwY2U4NWY4ZmEwNTM1ZmUifQ.J8_hICp4fawk0rrDY-GQOJDEaI_ZUZIYSH7gIogE1aNJjmK4pFEwBgmFozxt4grjoGX0kSp8AtcQdVW8LpX4gqSgV1lupieke3rLIaJNSlfruQXzPnTCpaqFn5w_wVc2bejhWDOQyzCOjy5SOdxSh9Y9O8vaC3TTE-ITgWgJ51StNwAtd0q4VO2ap3cAKO6BsAO-Gxqh4zzKBxER0nWI9XRwziMx3HcuB9PpQWP37ghNXblM_ULsVx2I-Y6lRGnnF071KDMwearno-lMqDCY3i_554TCizUhZgzBDhG_C5TMo7GNPp1_W67_9JR2yrU9KQ3KYrV-TTqQaXSBuF6CFg',
    'origin': 'https://seller.wildberries.ru',
    'priority': 'u=1, i',
    'referer': 'https://seller.wildberries.ru/',
    'sec-ch-ua': '"Opera GX";v="116", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0 (Edition Yx GX 03)'
}

    items_per_page = 100
    offset = 0
    max_pages = 10000  # Ограничимся, например, 50 страницами
    base_url = "https://seller-weekly-report.wildberries.ru/ns/trending-searches/suppliers-portal-analytics/api"

    page_count = 1

    while page_count < max_pages:
        url = f"{base_url}?itemsPerPage={items_per_page}&offset={offset}&period=month&query=&sort=desc"
        print(f"Запрашиваем offset={offset}...")

        if offset > 0 and offset % 30000 == 0:
            print(f"[fetch_popular_requests] offset={offset}, делаем паузу 20 минут, чтобы реже ловить 429...")
            time.sleep(1200)  # 20 мин

        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.RequestException as e:
            print(f"Ошибка при запросе: {e}")
            break

        if response.status_code == 429:
            # Too Many Requests
            print("[fetch_popular_requests] Получили 429 (Too Many Requests). Спим 2 минуты и пробуем снова...")
            time.sleep(120)
            # Не меняем offset/page_count, просто повторяем
            continue

        if response.status_code != 200:
            print(f"[fetch_popular_requests] Неожиданный статус {response.status_code}, прерываем.")
            break

        data_json = response.json()
        if data_json.get("error"):
            print(f"[fetch_popular_requests] Ошибка: {data_json.get('errorText', '')}")
            break

        data_block = data_json.get("data")
        if not data_block or "list" not in data_block:
            print("[fetch_popular_requests] Не найден ключ data['list'], завершаем.")
            break

        items = data_block["list"]
        if not items:
            print("[fetch_popular_requests] Пустой items, завершаем.")
            break

        for item in items:
            text_value = item.get("text", "")
            rc = item.get("requestCount", 0)
            if rc >= 300:
                pr = PopularRequest(
                    query_text = text_value,
                    request_count = rc,
                    load_date = datetime.datetime.utcnow()
                )
                session.add(pr)

        session.commit()

        offset += 10
        page_count += 1

    session.close()
    print("Сбор popular_requests завершён.")
