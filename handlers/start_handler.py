import datetime
from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from db.database import SessionLocal
from db.models import User, Token
from states.token_state import TokenState

async def cmd_start(message: types.Message, state: FSMContext):
    """
    Обработка /start.
    Проверяем, есть ли у пользователя привязанный WB-токен (через token_id).
    Если нет, просим отправить.
    """
    session = SessionLocal()

    # Ищем пользователя по telegram_id
    db_user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()

    if not db_user:
        # Создаём запись User (token_id=None значит нет токена)
        db_user = User(
            telegram_id=str(message.from_user.id),
            subscription_until=None,
            token_id=None
        )
        session.add(db_user)
        session.commit()

    # Если у пользователя есть token_id, значит уже привязан WB-токен
    if db_user.token_id is not None:
        # Для наглядности можем дополнительно проверить, что Token в таблице tokens существует:
        token_obj = session.query(Token).get(db_user.token_id)
        if token_obj is None:
            # На всякий случай, если token_id ссылается на несуществующую запись
            db_user.token_id = None
            session.commit()
            await message.answer(
                "У вас не найден валидный токен. Пожалуйста, пришлите ваш WB-токен."
            )
            await state.set_state(TokenState.waiting_for_token)
        else:
            # У пользователя действительно есть token
            await message.answer("Привет! Я WB Wizard. Рад снова тебя видеть.")
    else:
        # Если token_id нет - просим прислать токен
        await message.answer(
            "Привет! Я WB Wizard.\n"
            "Сначала нужно отправить мне ваш токен доступа к WB API.\n"
            "Пришлите его одним сообщением."
        )
        await state.set_state(TokenState.waiting_for_token)

    session.close()

def register_start_handler(dp: Dispatcher):
    # Регистрируем функцию cmd_start на команду /start
    dp.message.register(cmd_start, Command("start"))
