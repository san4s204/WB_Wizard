import datetime
import io
from db.database import SessionLocal
from db.models import Product
from PIL import Image as PILImage
from parse_wb import parse_wildberries
from core.wildberries_api import get_rating_and_feedbacks

async def update_products_if_outdated():
    """
    Проверяем товары, у которых last_update > 30 дней назад.
    Если старше - парсим с помощью parse_wildberries(url) и обновляем rating, reviews, image_url.
    Вставляем/обновляем resize_img (200x200) и last_update.
    """
    session = SessionLocal()

    # cutoff = сегодня - 30 дней
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=30)

    # 1) Берём товары, у которых last_update < cutoff
    products_to_update = session.query(Product).filter(Product.last_update < cutoff).all()
    print(f"[INFO] Найдено {len(products_to_update)} товаров для обновления (старше 30 дней).")

    for product in products_to_update:
        nm_id = product.nm_id
        if not nm_id:
            # Если нет nm_id, пропускаем
            continue

        # Генерируем ссылку на товар (по желанию можно использовать вашу логику)
        # Допустим, вы используете стандартный URL: "https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
        url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
        rating, reviews = await get_rating_and_feedbacks(nm_id)

        if rating is None or reviews is None:
            print(f"[SKIP] nm_id={nm_id} – карточка не найдена, пропускаем.")
            continue

        print(f"[INFO] Обновляем nm_id={nm_id}, URL={url}")
        try:
            parse_result = await parse_wildberries(url)
            # Ваш parse_wildberries(url) возвращает, например:
            # {
            #   "rating": "4.7",
            #   "reviews_count": "123",
            #   "image_url": "https://some..."
            # }
            # если у вас другой формат, адаптируйте

            # Достаём рейтинг (float), отзывы (int), image_url (str)
            rating_raw = rating if rating  is not None else "N/A"
            reviews_raw = reviews if reviews is not None else "N/A"
            new_image_url = parse_result.get("image_url", "")
            print("рейтинг = ", rating_raw, "\nотзывы = ",reviews_raw)

            

            # 3) Сохраняем в БД
            product.rating = rating
            product.reviews = reviews_raw
            product.image_url = new_image_url

            # 4) Если есть новое изображение, скачиваем и делаем resize_img
            if new_image_url and "не найден" not in new_image_url.lower():
                try:
                    import requests
                    resp = requests.get(new_image_url, timeout=10)
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
                    print(f"[WARN] Ошибка при скачивании/обработке картинки nm_id={nm_id}: {e}")

            # Обновляем last_update на сейчас
            product.last_update = datetime.datetime.utcnow()

            session.commit()

        except Exception as e:
            print(f"[ERROR] Не удалось обновить nm_id={nm_id}: {e}")
            # Можно continue или session.rollback() при необходимости

    session.close()
    print("[INFO] Обновление товаров (рейтинг, отзывы, картинка) завершено.")
