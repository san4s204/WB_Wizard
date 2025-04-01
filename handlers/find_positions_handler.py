from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
import asyncio
from core.parse_popular_req_products import find_article_in_current_city
from collections import defaultdict
from db.database import SessionLocal
from db.models import DestCity, User
from core.sub import get_user_role
# Предположим, ваша функция поиска:
# from core.search_tracker import find_article_in_search_async

user_states = defaultdict(lambda: "")

async def cmd_find_position_in_search(message: types.Message):
    """
    Хендлер для команды /find_position, которая ищет товар (nm_id) по ключевому запросу (query_text)
    в определённом городе (dest_value).
    
    Пример использования:
    /find_position 123456 637 кружка для чая
    """

    # Разбиваем текст
    args = message.text.split(maxsplit=2)
    # args[0] = "/find_positions"
    # args[1] = nm_id (если есть)
    # args[2] = query_text (если есть)

    # Если пользователь передал меньше 2 аргументов (т.е. вообще нет nm_id, query_text),
    # сообщаем формат
    if len(args) < 3:
        await message.answer(
            "Пожалуйста, введите данные в формате:\n"
            "<b>/find_positions &lt;nm_id&gt; &lt;ключевой_запрос&gt;</b>\n\n"
            "Например:\n"
            "<b>/find_positions 123456 кружка для чая</b>",
            parse_mode="HTML"
        )
        return

    # Парсим nm_id
    try:
        nm_id = int(args[1])
    except ValueError:
        await message.answer(
            "Ошибка: <b>nm_id</b> должен быть числом!\n"
            "Пример: <code>/find_positions 123456 кружка для чая</code>",
            parse_mode="HTML"
        )
        return

    query_text = args[2].strip()
    if not query_text:
        await message.answer(
            "Ошибка: не указан текст запроса!\n"
            "Пример: <code>/find_positions 123456 кружка для чая</code>",
            parse_mode="HTML"
        )
        return

    session = SessionLocal()
    db_user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
    if not db_user:
        session.close()
        await message.answer("Нет такого пользователя. Сначала /start.")
        return

    user_role = get_user_role(session, db_user)  # free, base, advanced, test, super...
    if user_role == "free":
        # Только 1 город - Москва
        await message.answer("Ищем ваш товар...")
        city_rows = [session.query(DestCity).filter_by(city="Москва").first()]  # (id, city, dest)
    else:
        await message.answer("Ищем ваш товар в 20 городах...")
        # Допустим, берем первые 20 из DestCity или все
        city_rows = session.query(DestCity).all()
    session.close()

    # Вызываем нашу функцию поиска (пример)
    results_dict = await find_article_in_current_city(nm_id, query_text, city_rows, max_pages=50)

    if not results_dict:
        await message.answer("Ошибка или нет городов в базе – результат пустой.")
        return

    # Собираем и выводим результаты
    session = SessionLocal()
    lines = []
    for city_id, (page, pos) in results_dict.items():
        city_obj = session.query(DestCity).get(city_id)
        city_name = city_obj.city if city_obj else f"[ID={city_id}]"
        if page is not None:
            lines.append(f"🏙 <b>{city_name}:</b> стр.{page}, позиция {pos}")
        else:
            lines.append(f"🏙 <b>{city_name}:</b> не найден")
    session.close()

    result_text = "\n".join(lines)
    if user_role == "free":
        await message.answer(
            f"<b>Результаты:</b>\n{result_text}\n"
            "Мы оставляем эту функцию бесплатной для вас!\n"
            "Взамен просим вас лишь подписаться на наш <a href='https://t.me/+kajuSJADWcBjZjli'>новостной канал</a>\n"
            "Желаете получить более подробную статистику? Оформите тариф Расшиернный!", 
            parse_mode="HTML")
    else:
        await message.answer(
            f"<b>Результаты:</b>\n{result_text}\n"
            "Будьте вкурсе свежих новостей, подпишитесь на наш <a href='https://t.me/+kajuSJADWcBjZjli'>новостной канал</a> ",
            parse_mode="HTML")

async def callback_search_cities(query: types.CallbackQuery):
    user_id = query.from_user.id
    # Установим состояние, что ждём сообщения вида "nm_id <пробел> query_text"
    user_states[user_id] = "await_search_input"

    await query.message.answer(
        "Введите nm_id и ключевой запрос (через пробел).\n"
        "Например: <code>123456 кружка для чая</code>",
        parse_mode="HTML"
    )
    await query.answer()

async def handle_user_message(message: types.Message):
    user_id = message.from_user.id
    state = user_states[user_id]

    if state == "await_search_input":
        # Сбрасываем сразу, чтобы одноразово
        user_states[user_id] = ""

        text = message.text.strip()
        # Нужно как-то разбирать: "nm_id query_text"
        # Если хотите nm_id+dest+query_text, придётся ещё иначе разбивать
        # Пока упрощённо: "12345 кружка для чая"
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Ошибка: введите nm_id и запрос через пробел.\nНапример: <code>123456 кружка для чая</code>")
            return

        try:
            nm_id = int(parts[0])
        except ValueError:
            await message.answer("nm_id должен быть числом!")
            return

        query_text = parts[1]

        session = SessionLocal()
        db_user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
        if not db_user:
            session.close()
            await message.answer("Нет такого пользователя. Сначала /start.")
            return

        user_role = get_user_role(session, db_user)  # free, base, advanced, test, super...
        if user_role == "free":
            # Только 1 город - Москва
            await message.answer("Ищем ваш товар...")
            city_rows = [session.query(DestCity).filter_by(city="Москва").first()]  # (id, city, dest)
        else:
            await message.answer("Ищем ваш товар в 20 городах...")
            # Допустим, берем первые 20 из DestCity или все
            city_rows = session.query(DestCity).all()
        session.close()

        # Вызываем нашу функцию поиска (пример)
        results_dict = await find_article_in_current_city(nm_id, query_text, city_rows, max_pages=50)

        if not results_dict:
            await message.answer("Что-то пошло не так, пустые результаты.")
            return

        # results -> dict { city_id: (page, pos) }
        # Можно достать из таблицы DestCity имя города
        session = SessionLocal()
        lines = []
        for city_id, (page, pos) in results_dict.items():
            dest_city = session.query(DestCity).get(city_id)
            city_name = dest_city.city if dest_city else f"ID={city_id}"

            if page is not None:
                lines.append(f"🏙 <b>{city_name}:</b> стр.{page}, позиция {pos}")
            else:
                lines.append(f"🏙 <b>{city_name}:</b> не найден")

        session.close()

        text_result = "\n".join(lines)
        if user_role == "free":
            await message.answer(
                f"<b>Результаты:</b>\n{text_result}\n"
                "Мы оставляем эту функцию бесплатной для вас!\n"
                "Взамен просим вас лишь подписаться на наш <a href='https://t.me/+kajuSJADWcBjZjli'>новостной канал</a>\n"
                "Желаете получить более подробную статистику? Оформите тариф Расшиернный!", 
                parse_mode="HTML")
        else:
            await message.answer(
                f"<b>Результаты:</b>\n{text_result}\n"
                "Будьте вкурсе свежих новостей, подпишитесь на наш <a href='https://t.me/+kajuSJADWcBjZjli'>новостной канал</a> ",
                parse_mode="HTML")

    else:
        # Если пользователь не в процессе ввода nm_id/query_text, можете либо игнорировать,
        # либо отвечать чем-то другим
        await message.answer("Я пока не знаю, что с этим сообщением сделать.")

def register_find_position_handlers(dp: Dispatcher):
    """
    Регистрируем наш хендлер в диспатчере Aiogram 3.x
    """
    dp.callback_query.register(callback_search_cities, lambda c: c.data =="find_position")
    dp.message.register(cmd_find_position_in_search, Command("find_positions"))
    dp.message.register(handle_user_message, F.text & ~F.command)
