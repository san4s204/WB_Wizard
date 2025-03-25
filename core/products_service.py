from db.database import SessionLocal
from db.models import Product
from sqlalchemy.orm import Session
from parse_wb import parse_wildberries
import datetime
import re
import requests
import io
import PIL.Image as PILImage
from db.models import Order, Product

async def fill_new_products_from_orders():
    """
    Проходит по таблице Orders, находит все уникальные nm_id (с учётом token_id),
    и если в таблице Products ещё нет такой записи, создаёт её.
    """
    session: Session = SessionLocal()

    # 1) Находим все уникальные комбо (token_id, nm_id, subject, brand, supplier_article, techSize)
    #    Можем делать distinct() сразу по нужным полям
    results = (
        session.query(
            Order.token_id,
            Order.nm_id,
            Order.subject,
            Order.brand,
            Order.supplier_article,
            Order.techSize
        )
        .filter(Order.nm_id.isnot(None))  # пропустим, если nm_id = None
        .distinct(
            Order.token_id,
            Order.nm_id
        )
        .all()
    )

    print(f"Найдено {len(results)} уникальных пар (token_id, nm_id) в orders.")

    # Закроем сессию и откроем заново внутри цикла или передадим session внутрь upsert_product
    # (Если upsert_product сама создает session, то нам достаточно list(…)
    session.close()

    # 2) Идём в цикле по найденным записям
    for row in results:
        token_id = row[0]
        nm_id = row[1]
        subject_name = row[2] or ""
        brand_name = row[3] or ""
        supplier_article = row[4] or ""
        techSize = row[5] or ""

        # 3) Вызываем upsert_product (асинхронную)
        #    Предполагая, что upsert_product сама создаёт SessionLocal()
        await upsert_product(
            nm_id=nm_id,
            subject_name=subject_name,
            brand_name=brand_name,
            supplier_article=supplier_article,
            token_id=token_id,
            techSize=techSize
        )

    print("Заполнение новой таблицы Products из Orders завершено.")

async def upsert_product(nm_id: int, subject_name: str, brand_name: str, supplier_article: str, token_id: int, techSize: str):
    """
    Создаёт или обновляет запись в таблице products по nm_id.
    + Загружает данные (rating, reviews, image_url) через parse_wildberries()
    + Скачивает и сохраняет "resize_img" (200x200) в BLOB
    """

    session: Session = SessionLocal()
    product = session.query(Product).filter_by(nm_id=nm_id).first()

    if not product:
        product = Product(
            token_id=token_id,
            nm_id=nm_id,
            subject_name=subject_name,
            brand_name=brand_name,
            supplier_article=supplier_article,
            techSize=techSize,
            last_update=datetime.datetime.utcnow()
        )

        # 1) Парсим данные c WB (rating, reviews, image_url)
        wb_url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
        parse_result = await parse_wildberries(wb_url)

        rating_str = parse_result.get("rating", "")
        reviews_str = parse_result.get("reviews", "")
        reviews_str = re.sub(r"[^\d]", "", reviews_str)  # оставляем только цифры
        image_url = parse_result.get("image_url", "")

        # Преобразуем rating, reviews из строк в числа (если получается)
        try:
            product.rating = float(rating_str.replace(",", "."))  # например "4,7" -> 4.7
        except:
            product.rating = None

        try:
            product.reviews = int(reviews_str)
        except:
            product.reviews = None

        product.image_url = image_url

        # 2) Если image_url валидный, скачаем картинку и сохраним в resize_img (200x200)
        if image_url and "не найден" not in image_url.lower():
            try:
                resp = requests.get(image_url, timeout=10)
                if resp.status_code == 200:
                    pil_img = PILImage.open(io.BytesIO(resp.content))

                    # Масштабируем до 200x200
                    pil_img = pil_img.resize((200, 200), PILImage.Resampling.LANCZOS)

                    out_bytes = io.BytesIO()
                    pil_img.save(out_bytes, format="PNG")
                    out_bytes.seek(0)

                    # Записываем сырые байты PNG в поле resize_img
                    product.resize_img = out_bytes.getvalue()
            except Exception as e:
                print(f"Ошибка при скачивании/обработке картинки для nm_id={nm_id}: {e}")

        session.add(product)
        session.commit()
    else:
        product.subject_name = subject_name
        product.brand_name = brand_name
        product.supplier_article = supplier_article
        product.last_update = datetime.datetime.utcnow()


        # 3) Сохраняем изменения
        session.commit()
        session.close()

def update_product_rating_reviews(nm_id: int, rating: float, reviews: int, image_url: str = None):
    """
    Если парсер получил новые rating / reviews / image_url — сохраняем в БД.
    """
    session: Session = SessionLocal()
    product = session.query(Product).filter_by(nm_id=nm_id).first()
    if product:
        product.rating = rating
        product.reviews = reviews
        if image_url:
            product.image_url = image_url
        product.last_update = datetime.datetime.utcnow()
        session.commit()
    session.close()


def update_product_details_from_parser():
    """
    Обновляет данные (рейтинг, отзывы, image_url) для товаров из таблицы `products`,
    используя парсер `parse_wildberries`.
    """
    print("Запуск обновления данных для товаров из таблицы `products`.")
    session: Session = SessionLocal()

    # Извлекаем все товары из таблицы products
    products_to_update = session.query(Product).all()

    print(f"Найдено {len(products_to_update)} товаров для обновления.")

    for product in products_to_update:
        nm_id = product.nm_id
        url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"

        print(f"Обрабатываем товар nm_id={nm_id} ({url})...")
        try:
            # Запускаем парсер для получения данных
            parse_result = parse_wildberries(url)

            if parse_result:
                rating_raw = parse_result.get("rating")
                rating = float(rating_raw.replace(",", ".")) if rating_raw else None


                reviews_raw = parse_result.get("reviews", "")
                reviews = int(re.sub(r"[^\d]", "", reviews_raw))

                product.rating = rating
                product.reviews = reviews
                product.image_url = parse_result.get("image_url")
                product.last_update = datetime.datetime.utcnow()

                print(f"Обновлено: рейтинг={product.rating}, отзывы={product.reviews}, image_url={product.image_url}")
            else:
                print(f"Парсер не смог получить данные для nm_id={nm_id}. Пропускаем.")

        except Exception as e:
            print(f"Ошибка при обработке nm_id={nm_id}: {e}")

    # Сохраняем изменения
    session.commit()
    session.close()
    print("Обновление завершено.")