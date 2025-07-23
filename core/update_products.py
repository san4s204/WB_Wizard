import datetime
import io
import logging
import sys
from db.database import SessionLocal
from db.models import Product
from PIL import Image as PILImage
from parse_wb import parse_wildberries
from core.wildberries_api import get_rating_and_feedbacks


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("update_log.log")
    ]
)
logger = logging.getLogger(__name__)

async def update_products_if_outdated():
    """
    Проверяет товары, у которых last_update > 30 дней назад или rating/reviews=NULL.
    Парсит актуальные данные с помощью parse_wildberries(url) и обновляет рейтинг, отзывы, image_url.
    Создаёт/обновляет миниатюру изображения (resize_img) размером 200x200 пикселей и устанавливает current timestamp в last_update.
    """
    logger.info("Начало процедуры обновления товаров...")
    
    session = SessionLocal()
    
    # Определяем границу дат для отбора товаров (30 дней назад)
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    
    # Выбираем товары, удовлетворяющие условиям фильтрации
    products_to_update = session.query(Product).filter(
        (Product.last_update < cutoff_date) |
        (Product.rating.is_(None)) |
        (Product.reviews.is_(None))
    ).all()
    
    logger.info(f"Найдено {len(products_to_update)} товаров для обновления.")
    
    for idx, product in enumerate(products_to_update, start=1):
        nm_id = product.nm_id
        if not nm_id:
            logger.warning(f"Пропускаем продукт #{product.id} (нет nm_id)")
            continue
        
        logger.info(f"{idx}/{len(products_to_update)}. Обрабатываю nm_id={nm_id}")
        
        # Получаем рейтинг и количество отзывов
        rating, reviews = await get_rating_and_feedbacks(nm_id)
        
        if rating is None or reviews is None:
            logger.warning(f"Карточка nm_id={nm_id} не найдена, пропускаем.")
            continue
        
        # Формируем URL товара
        url = f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx"
        
        # Парсим страницу товара
        try:
            parse_result = await parse_wildberries(url)
        except Exception as e:
            logger.error(f"Ошибка при парсинге nm_id={nm_id}: {e}")
            continue
        
        # Обновляем рейтинг и отзывы
        product.rating = float(rating) if rating is not None else None
        product.reviews = int(reviews) if reviews is not None else None
        
        # Обновляем URL изображения
        new_image_url = parse_result.get("image_url", "")
        product.image_url = new_image_url
        
        # Загружаем и масштабируем изображение до размера 200x200 px
        if new_image_url and "не найден" not in new_image_url.lower():
            try:
                from PIL import Image
                import requests
                from io import BytesIO
                
                response = requests.get(new_image_url, stream=True, timeout=10)
                response.raise_for_status()
                
                img = Image.open(BytesIO(response.content)).convert("RGB")
                resized_img = img.resize((200, 200), resample=Image.Resampling.LANCZOS)
                
                output_buffer = BytesIO()
                resized_img.save(output_buffer, format="JPEG")
                output_buffer.seek(0)
                
                product.resize_img = output_buffer.read()
            except Exception as ex:
                logger.warning(f"Ошибка при обработке изображения nm_id={nm_id}: {ex}")
        
        # Устанавливаем отметку времени последнего обновления
        product.last_update = datetime.datetime.utcnow()
        
        # Фиксируем изменения в базе данных
        try:
            session.commit()
            logger.info(f"Успешно обновлён nm_id={nm_id}")
        except Exception as exc:
            session.rollback()
            logger.error(f"Ошибка сохранения nm_id={nm_id}: {exc}")
    
    session.close()
    logger.info("Завершение процедуры обновления товаров.")
