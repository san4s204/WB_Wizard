from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium_stealth import stealth


import time

async def parse_wildberries(url: str):
    service = Service(r"C:\Users\paaku\Desktop\WB Wizard\chromedriver-win64\chromedriver.exe")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # если нужен режим без UI
    options.add_argument('--window-size=1920,1080')     # Задать размер окна, чтобы элементы верстки появлялись

    driver = webdriver.Chrome(service=service, options=options)

     # Подключаем stealth
    stealth(
        driver,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/108.0.0.0 Safari/537.36",
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    try:
        driver.get(url)

        # 1) Ждём появления заголовка (названия товара)
        title_element = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
        )
        title = title_element.text

        time.sleep(10)

        # 2) Прокручиваем страницу вниз (чтобы динамика подгрузилась)
        driver.execute_script("window.scrollTo(0, 2000);")

        # 3) Даем побольше времени на подгрузку контента
        time.sleep(20)


        # -- Рейтинг
        try:
            rating_element = driver.find_element(
                By.CSS_SELECTOR,
                "span.product-review__rating.address-rate-mini.address-rate-mini--sm"
            )
            rating = rating_element.text
        except:
            rating = "Рейтинг не найден"

        # -- Количество отзывов
        try:
            reviews_element = driver.find_element(
                By.CSS_SELECTOR,
                "span.product-review__count-review.j-wba-card-item-show.j-wba-card-item-observe"
            )
            reviews_count = reviews_element.text
        except:
            reviews_count = "Отзывы не найдены"

    

        # -- Поиск картинки

        # СПОСОБ А: Ищем именно тег <img>, если на скриншоте действительно img, 
        # к примеру: <img class="photo-zoom__preview j-zoom-image ..." src="...">
        try:
            image_element = driver.find_element(
                By.CSS_SELECTOR,  # ищем img по двум классам
                "img.photo-zoom__preview.j-zoom-image"
            )
            image_url = image_element.get_attribute("src")
        except:
            image_url = "URL картинки не найден"

        try:
            # На странице она может быть тегом <a class="seller-info__title ...">
            store_link_element = driver.find_element(
                By.CSS_SELECTOR,
                "a.seller-info__title.seller-info__title--link.j-wba-card-item"
            )
            store_link = store_link_element.get_attribute("href")
        except:
            store_link = "Ссылка на магазин не найдена"

        return {
            "title": title,
            "rating": rating,
            "reviews": reviews_count,
            "image_url": image_url,
            "store_link": store_link,
        }


    except Exception as e:
        print(f"[parse_wildberries] Ошибка: {e}")
        # При любой ошибке всё равно возвращаем словарь
        return {
            "title": "",
            "rating": "",
            "reviews": "",
            "image_url": "",
            "store_link": ""
        }

    finally:
        driver.quit()


if __name__ == '__main__':
    url = "https://www.wildberries.ru/catalog/152649654/detail.aspx"
    parse_wildberries(url)


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