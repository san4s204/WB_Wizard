from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import datetime

from utils.logger import logger
from db.database import SessionLocal
from db.models import User
from core.wildberries_api import get_seller_info  # функция из пункта 1
from core.sub import get_user_role  

async def cmd_cabinet(message: types.Message, user_id: int = None):
    """
    Хендлер для "/cabinet". Показывает личный кабинет:
    - Название магазина (из WB API)
    - Тариф (пока "Тестовый")
    - Срок подписки (пока захардкожено, напр. до 20.02.2025)
    И набор кнопок (Показать магазины, Сводная инф., Отчёты, Настройки).
    """
    # Удаляем прошлое сообщение
    await message.delete()

    if user_id is None:
        # Значит вызвали напрямую командой /cabinet, берём message.from_user.id
        user_id = message.from_user.id

     # Открываем сессию, ищем user
    session = SessionLocal()
    db_user = session.query(User).filter_by(telegram_id=str(user_id)).first()
    if not db_user:
        session.close()
        await message.answer("Пользователь не найден. Попробуйте /start.")
        return

    token_obj = db_user.token
    if not token_obj:
        session.close()
        await message.answer("У вас не привязан токен. Сначала /start.")
        return

    user_token_value = token_obj.token_value  # Сам token string
    tariff = get_user_role(session, db_user)  # Возвращает 'free','base','advanced','test','super' и т.д.
    subscription_until = token_obj.subscription_until

    # Берём store_link из БД (может быть None, если ещё не был сохранён)
    store_link = db_user.store_link or ""
    tariff = get_user_role(session, db_user)  # роль токена

    session.close()

    # 1. Получаем название магазина через get_seller_info
    try:
        seller_data = get_seller_info(user_token_value)
        store_name = seller_data.get("name", "Неизвестный магазин")
    except Exception as e:
        logger.error(f"Ошибка при получении названия магазина: {e}")
        store_name = "Ошибка при запросе"

    # Если есть ссылка, делаем гиперссылку
    # Если ссылки нет — просто показываем store_name
    if store_link:
        store_label = f"<a href='{store_link}'>{store_name}</a>"
    else:
        store_label = store_name  # без ссылки




    # 3. Формируем текст сообщения
    text = (
        f"👤 <b>Личный кабинет</b>\n"
        f"Магазин: {store_label}\n"
        f"Тариф: {tariff}\n"
        f"Доступ до {subscription_until.strftime('%d.%m.%Y %H:%M:%S')}"
    )

    # 4. Формируем inline-клавиатуру
    #    Пример: 4 кнопки в столбик
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Просмотреть список заказов", callback_data="orders")
    kb_builder.button(text="Cводный отчёт", callback_data="my_products")
    kb_builder.button(text="Поддержка", callback_data="help")
    kb_builder.button(text="Настройки", callback_data="settings")
    kb_builder.adjust(2)  # по 2 кнопке в ряд

    # Отправляем сообщение
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb_builder.as_markup()
    )

def register_cabinet_handler(dp: Dispatcher):
    dp.message.register(cmd_cabinet, Command("cabinet"))
