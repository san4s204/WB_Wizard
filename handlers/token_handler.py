# handlers/token_handler.py
import datetime
from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states.token_state import TokenState
from db.database import SessionLocal
from db.models import User, Order, Token
from core.products_service import upsert_product
from core.fill_orders import fill_orders
from parse_wb import parse_wildberries

# Пример: период 30 дней
PERIOD_DAYS = 90

# Период забора данных за 90 дней
date_from_str = (datetime.datetime.now() - datetime.timedelta(days=PERIOD_DAYS)).strftime('%Y-%m-%d')

def is_valid_wb_token(token: str) -> bool:
    """Простейшая проверка: строка должна содержать минимум 2 точки и быть длиной > 50."""
    if token.count(".") < 2:
        return False
    if len(token) < 50:
        return False
    return True

async def process_token(message: types.Message, state: FSMContext):
    """
    Срабатывает, когда пользователь находится в TokenState.waiting_for_token
    и присылает текст (считаем это WB-токеном).
    """
    wb_token = message.text.strip()

    # 1) Сохраняем в БД
    session = SessionLocal()
    db_user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
    if not db_user:
        session.close()
        await message.answer("Ошибка: пользователь не найден. Попробуйте /start заново.")
        await state.clear()
        return
    # Простейшая проверка
    if not is_valid_wb_token(wb_token):
        await message.answer(
            "Кажется, это не похоже на токен. "
            "Убедитесь, что вы скопировали токен целиком, включая точки.\n"
            "Попробуйте ещё раз или /cancel, чтобы отменить."
        )
        return

    # Ищем в таблице tokens
    existing_token = session.query(Token).filter_by(token_value=wb_token).first()
    if not existing_token:
        # Создаём новую запись Token
        new_token = Token(
            token_value=wb_token,
            role="test",  # Назначаем 'test'
            subscription_until=datetime.datetime.utcnow() + datetime.timedelta(days=30)  # +30 дней
        )
        session.add(new_token)
        session.commit()
        token_id = new_token.id
    else:
        token_id = existing_token.id

    # Привязываем user.token_id
    db_user.token_id = token_id
    session.commit()
    session.close()

    if not existing_token:
        await message.answer(
            "Токен сохранён и привязан к вашему аккаунту! "
            "Вы получили <b>тестовый режим</b> на 30 дней. "
            "Приятного пользования ботом!",
            parse_mode="HTML"
        )
    else:
        await message.answer("Токен сохранён и привязан к вашему аккаунту!")

    
    # 2) Вызываем save_report_details (например, за 30 дней)
    await message.answer(f"Сохраняю отчёты за последние {PERIOD_DAYS} дней...")
    # Предполагается, что функция save_report_details(...) синхронная.
    # Если она очень долгая, можно вынести в ThreadPool или Celery.

    await fill_orders(date_from_str, telegram_id=str(message.from_user.id))

    session2 = SessionLocal()
    db_user2 = session2.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
    if not db_user2 or not db_user2.token_id:
        session2.close()
        await message.answer("Не найдено ни одного nm_id (нет token_id).")
        return

    # Фильтруем заказы (Order.token_id == db_user2.token_id)
    nm_ids = (
        session2.query(Order.nm_id)
        .filter(Order.token_id == db_user2.token_id)
        .distinct()
        .all()
    )

    upsert_count = 0
    first_nm_id = None
    for (nm_id,) in nm_ids:
        if first_nm_id is None:
            first_nm_id = nm_id
        # Нужно ещё узнать subject, brand, article — см. у вас в report_details
        # Или можно взять "заглушки", если в report_details есть поля subject_name, ...
        detail = session.query(Order).filter_by(nm_id=nm_id).first()
        if detail:
            token_id = detail.token_id
            subject_name = detail.subject or "unknown"
            brand_name = detail.brand or "unknown"  # если нужно
            supplier_article = detail.supplier_article or "unknown"  # если нужно
            techSize = detail.techSize

            await upsert_product(nm_id, subject_name, brand_name, supplier_article, token_id, techSize)
            upsert_count += 1

    if first_nm_id:
        url = f"https://www.wildberries.ru/catalog/{first_nm_id}/detail.aspx"
        parse_result = await parse_wildberries(url)  # получаем { ... "store_link": ... }

        store_link = parse_result.get("store_link", "")
        if store_link:
            # Открываем новую сессию, чтобы сохранить user.store_link
            session2 = SessionLocal()
            db_user2 = session2.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
            if db_user2:
                db_user2.store_link = store_link
                session2.commit()
                await message.answer(f"Ссылка на магазин получена и сохранена:\n{store_link}")
            session2.close()
        else:
            await message.answer("Не удалось получить ссылку на магазин.")
    else:
        await message.answer("Не найдено ни одного nm_id в таблице orders...")

    session.close()

    # 4) Сообщаем пользователю
    await message.answer(
        f"Готово! Теперь бот готов к работе."
    )

    # Очищаем state
    await state.clear()

def register_token_handler(dp: Dispatcher):
    """
    Регистрируем обработчик, который ловит ответ в состоянии TokenState.waiting_for_token
    """
    dp.message.register(process_token, TokenState.waiting_for_token)
