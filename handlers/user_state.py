from aiogram import Dispatcher, types
from aiogram import F
import datetime
from core.parse_popular_req_products import find_article_in_current_city
from db.database import SessionLocal
from db.models import DestCity, User
from core.sub import get_user_role
from handlers.generate_report_day_handler import generate_excel_report_for_date
from states.user_state import user_states
# Предположим, ваша функция поиска:
# from core.search_tracker import find_article_in_search_async


async def handle_user_message(message: types.Message):
    user_id = message.from_user.id
    user_state = user_states[user_id]

    print("user_states =", dict(user_states))  # лог в консоль
    print("current user_id =", user_id)
    print("CURRENT STATE:", user_states[user_id])

    # Команда отмены
    if message.text.strip().lower() == "/cancel":
        user_states[user_id] = {}
        await message.answer("Режим поиска отменён.")
        return

    # Этап 1 — ввод артикул
    if user_state.get("state") == "await_article_input":
        try:
            nm_id = int(message.text.strip())
        except ValueError:
            await message.answer("❗ Артикул должен быть числом. Попробуйте снова или введите /cancel.")
            return

        user_states[user_id] = {
            "state": "await_query_input",
            "nm_id": nm_id
        }
        await message.answer("Теперь введите ключевой запрос для поиска.\nНапример: <code>кружка для чая</code>", parse_mode="HTML")
        return

    # Этап 2 — ввод запроса
    if user_state.get("state") == "await_query_input":
        nm_id = user_state.get("nm_id")
        query_text = message.text.strip()
        user_states[user_id] = {}  # сбрасываем состояние

        if not query_text:
            await message.answer("❗ Запрос не должен быть пустым. Введите /find_positions, чтобы начать заново.")
            return

        # далее — та же логика как у тебя выше (поиск и ответ):
        session = SessionLocal()
        db_user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
        if not db_user:
            session.close()
            await message.answer("Нет такого пользователя. Сначала /start.")
            return

        user_role = get_user_role(session, db_user)
        if user_role == "free":
            await message.answer("Ищем ваш товар...")
            city_rows = [session.query(DestCity).filter_by(city="Москва").first()]
        else:
            await message.answer("Ищем ваш товар в 20 городах...")
            city_rows = session.query(DestCity).all()
        session.close()

        results_dict = await find_article_in_current_city(nm_id, query_text, city_rows, max_pages=50)

        if not results_dict:
            await message.answer("Что-то пошло не так, пустые результаты.")
            return

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
                "Желаете получить более подробную статистику? Оформите тариф Расширенный!", 
                parse_mode="HTML")
        else:
            await message.answer(
                f"<b>Результаты:</b>\n{text_result}\n"
                "Будьте в курсе свежих новостей, подпишитесь на наш <a href='https://t.me/+kajuSJADWcBjZjli'>новостной канал</a>",
                parse_mode="HTML")
        return
    
    if user_state.get("state") == "await_report_date":
        day_str = message.text.strip()
        user_states[user_id] = {}  # сбрасываем

        # Валидация даты
        try:
            datetime.datetime.strptime(day_str, "%Y-%m-%d")
        except ValueError:
            await message.answer("❗ Неверный формат даты. Используйте <b>YYYY-MM-DD</b>.\nПример: <code>2025-03-25</code>", parse_mode="HTML")
            return

        # Достаём токен
        session = SessionLocal()
        db_user = session.query(User).filter_by(telegram_id=str(user_id)).first()
        if not db_user or not db_user.token_id:
            session.close()
            await message.answer("У вас не привязан токен. Сначала выполните /start или настройку.")
            return

        token_id = db_user.token_id
        session.close()

        # Генерация отчета
        try:
            excel_bytes = await generate_excel_report_for_date(token_id, day_str)
        except ValueError as e:
            await message.answer(f"Ошибка при формировании отчёта: {e}")
            return

        if len(excel_bytes) > 50_000_000:
            await message.answer("❗ Файл отчета слишком большой для отправки через Telegram.")
            return

        await message.answer_document(
            document=types.BufferedInputFile(excel_bytes, filename=f"report_{day_str}.xlsx"),
            caption=f"Отчёт за {day_str}"
        )
        return

    # По умолчанию
    await message.answer("Я пока не знаю, что с этим сообщением делать. Напишите /cancel или используйте команду.")

def register_common_text_handler(dp: Dispatcher):
    """
    Регистрируем наш хендлер в диспатчере Aiogram 3.x
    """
    dp.message.register(handle_user_message, F.text & ~F.command)