from db.models import Media
from db.database import SessionLocal
import os
from datetime import datetime

# Путь к вашему изображению (замените на реальный путь!)
IMAGE_PATH = 'поставка.png'

def upload_image_to_db(image_path: str):
    """
    Загружает одно PNG-изображение в базу данных.
    """
    # Проверяем существование файла
    if not os.path.exists(image_path):
        print(f"❗️ Ошибка: файл '{image_path}' не найден!")
        return

    # Создаем сессию к базе данных
    session = SessionLocal()

    try:
        # Читаем бинарные данные изображения
        with open(image_path, 'rb') as f:
            image_binary = f.read()

        # Создаем запись в базе данных
        media_entry = Media(
            filename=os.path.basename(image_path),
            resize_img=image_binary,
            created_at=datetime.utcnow()
        )

        # Добавляем запись и фиксируем транзакцию
        session.add(media_entry)
        session.commit()

        print(f"✅ Изображение '{os.path.basename(image_path)}' успешно загружено в базу данных!")

    except Exception as e:
        session.rollback()
        print(f"❗️ Произошла ошибка: {e}")

    finally:
        session.close()

if __name__ == '__main__':
    upload_image_to_db(IMAGE_PATH)