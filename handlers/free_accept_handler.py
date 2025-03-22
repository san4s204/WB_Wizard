# handlers/settings_handler.py
from aiogram import types
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from db.database import SessionLocal
from db.models import User, UserWarehouse, AcceptanceCoefficient
from collections import defaultdict
from aiogram import Dispatcher
from core.sub import get_user_role

user_pages = defaultdict(lambda: 0)  # user_pages[user_id] = current_page

def get_all_warehouses(token_id: int) -> list[tuple]:
    """
    Возвращаем список (warehouse_id, warehouseName).
    Можно брать из AcceptanceCoefficient или другого справочника.
    Пример: уникальные склад_id из ближайших 14 дней.
    """
    session = SessionLocal()
    rows = session.query(
        AcceptanceCoefficient.warehouse_id,
        AcceptanceCoefficient.warehouse_name
    )\
    .filter_by(token_id=token_id)\
    .distinct()\
    .all()
    session.close()

    return [(r[0], r[1]) for r in rows if r[0] and r[1]]

async def callback_track_free_accept_menu(query: CallbackQuery):
    """
    Показывает первую страницу складов (или текущую, если уже установлена).
    """
    user_id = query.from_user.id
    session = SessionLocal()
    db_user = session.query(User).filter_by(telegram_id=str(user_id)).first()
    if not db_user:
        session.close()
        await query.answer("Пользователь не найден.")
        return

    # Получаем список всех складов
    all_warehouses = get_all_warehouses(db_user.token_id)
    if not all_warehouses:
        session.close()
        await query.message.edit_text("Список складов пуст или не найден.")
        await query.answer()
        return

    # Запоминаем 0-ю страницу, если её ещё нет
    if user_id not in user_pages:
        user_pages[user_id] = 0
    current_page = user_pages[user_id]

    # Рендерим inline-клавиатуру
    kb = InlineKeyboardBuilder()
    page_size = 6
    start_i = current_page * page_size
    end_i = start_i + page_size
    slice_wh = all_warehouses[start_i:end_i]  # 6 штук

    # У пользователя - какие склады уже подписаны?
    wh_builder = InlineKeyboardBuilder()
    user_whs = session.query(UserWarehouse).filter_by(user_id=db_user.id).all()
    subscribed_ids = {x.warehouse_id for x in user_whs}

    for (wh_id, wh_name) in slice_wh:
        # Проверяем, подписан ли user
        subscribed = (wh_id in subscribed_ids)
        if subscribed:
            wh_builder.button(text=f"✅ {wh_name}", callback_data=f"del_wh_{wh_id}")
        else:
            wh_builder.button(text=f"🚫 {wh_name}", callback_data=f"add_wh_{wh_id}")
    wh_builder.adjust(3)  # складские кнопки по 3 в ряд)  # по одной кнопке в ряд

    # Навигация (назад/вперёд)
    # Если есть пред.страница
    nav_builder = InlineKeyboardBuilder()
    if current_page > 0:
        nav_builder.button(text="⬅️Назад", callback_data="track_free_accept_prev")
    # Если есть след.страница
    max_page = (len(all_warehouses) - 1) // page_size  # целочисленное деление
    if current_page < max_page:
        nav_builder.button(text="Вперёд➡️", callback_data="track_free_accept_next")
    nav_builder.adjust(2)  # две кнопки в ряд (если обе есть)

    # Кнопка "Назад" (в меню)
    nav_builder.button(text="Выход", callback_data="cabinet")
    nav_builder.adjust(1)

    # -- «Склеиваем» две разметки
    wh_markup = wh_builder.as_markup()
    nav_markup = nav_builder.as_markup()

    # Объединяем все ряды в один InlineKeyboardMarkup
    combined_rows = wh_markup.inline_keyboard + nav_markup.inline_keyboard
    combined_kb = InlineKeyboardMarkup(inline_keyboard=combined_rows)

    text = f"<b>Трекинг бесплатной приёмки</b>\n" \
           f"Подпишитесь✅ на склады, чтобы получить уведомление \n о бесплатной приёмке на выбранный склад\n" \
           f"Всего складов: {len(all_warehouses)}\n" \
           f"Текущая страница: {current_page + 1}/{max_page + 1}\n\n" \
           f"Всего подписок: {len(subscribed_ids)}\n" \
           f"Выберите склад для добавления/удаления:"
    session.close()
    await query.message.edit_text(text, reply_markup=combined_kb)
    await query.answer()

async def callback_track_free_accept_prev(query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in user_pages:
        user_pages[user_id] = 0
    if user_pages[user_id] > 0:
        user_pages[user_id] -= 1
    # Перерисовать то же меню
    await callback_track_free_accept_menu(query)

async def callback_track_free_accept_next(query: CallbackQuery):
    user_id = query.from_user.id
    user_pages[user_id] += 1
    await callback_track_free_accept_menu(query)

async def callback_add_wh(query: CallbackQuery):
    """
    Callback вида add_wh_12345
    """

    ROLE_WAREHOUSE_LIMITS = {
    "free": 1,
    "base": 3,
    "test": 9,
    "advanced": 9,
    "super": None  # None = безлимит
}

    data = query.data  # "add_wh_12345"
    _, _, wh_str = data.partition("add_wh_")
    if not wh_str.isdigit():
        await query.answer("Некорректный склад.")
        return
    wh_id = int(wh_str)

    session = SessionLocal()
    db_user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    if not db_user:
        session.close()
        await query.answer("Пользователь не найден.")
        return

    # Считаем, сколько у него уже
    count_warehouses = session.query(UserWarehouse).filter_by(user_id=db_user.id).count()

    # Определяем роль
    user_role = get_user_role(session, db_user)  # "free","base","advanced","test","super"

    # Получаем лимит
    limit = ROLE_WAREHOUSE_LIMITS.get(user_role, 0)
    # Если None => без лимита
    if limit is not None and count_warehouses >= limit:
        session.close()
        await query.answer(
            f"Ваш тариф '{user_role}' допускает максимум {limit} складов.\n"
            "Сначала удалите что-то прежде чем добавлять."
        )
        return

    # Проверяем, не существует ли
    exists = session.query(UserWarehouse).filter_by(user_id=db_user.id, warehouse_id=wh_id).first()
    if exists:
        session.close()
        await query.answer("Этот склад уже подписан.")
        return

    new_rec = UserWarehouse(user_id=db_user.id, warehouse_id=wh_id)
    session.add(new_rec)
    session.commit()
    session.close()

    await query.answer("Склад добавлен.")
    # Обновим меню
    await callback_track_free_accept_menu(query)

async def callback_del_wh(query: CallbackQuery):
    """
    Callback вида del_wh_12345
    """
    data = query.data  # "del_wh_12345"
    _, _, wh_str = data.partition("del_wh_")
    if not wh_str.isdigit():
        await query.answer("Некорректный склад.")
        return
    wh_id = int(wh_str)

    session = SessionLocal()
    db_user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    if not db_user:
        session.close()
        await query.answer("Пользователь не найден.")
        return

    record = session.query(UserWarehouse).filter_by(user_id=db_user.id, warehouse_id=wh_id).first()
    if record:
        session.delete(record)
        session.commit()
        session.close()
        await query.answer("Склад удалён.")
    else:
        session.close()
        await query.answer("У вас нет подписки на этот склад.")

    # Обновим меню
    await callback_track_free_accept_menu(query)