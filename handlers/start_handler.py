import datetime
from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.types import CallbackQuery
from db.database import SessionLocal
from db.models import User, Token
from states.token_state import TokenState

SAFETY_TEXT = (
    "<b>🔒 Безопасность</b>\n\n"
    "1️⃣ Наш бот использует ваш API-токен лишь для чтения статистики: заказов, остатков и т.д.\n"
    "2️⃣ Он не умеет изменять цены, карточки товаров или доступ к вашему личному кабинету.\n"
    "3️⃣ Вы можете в любой момент отозвать ключ в личном кабинете Wildberries.\n"
    "4️⃣ Все данные хранятся на защищённых серверах и не передаются третьим лицам.\n\n"

    "⚙️ Функциональность\n\n"
    "• 🛍 Отслеживание заказов, выкупов, отказов\n"
    "• 🚚 Уведомления о бесплатной приёмке\n"
    "• 🔎 Поиск позиции товара по ключевому запросу\n"
    "• 📊 Сводная статистика в Excel\n"
    "• И многое другое (см. /tariffs)\n\n"

    "Если у вас остались вопросы – напишите /help, мы на связи🙌"
)

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

    # Проверяем, есть ли у пользователя token_id
    if db_user.token_id is not None:
        # Для наглядности можем проверить, что Token действительно существует
        token_obj = session.query(Token).get(db_user.token_id)
        if token_obj is None:
            # На всякий случай, если token_id "битый"
            db_user.token_id = None
            session.commit()
            # Просим заново прислать токен
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(text="Это безопасно?", callback_data="is_safe")
            kb_builder.adjust(1)

            await message.answer(
                "У вас не найден валидный токен. Пожалуйста, пришлите ваш WB-токен.",
                reply_markup=kb_builder.as_markup()
            )
            await state.set_state(TokenState.waiting_for_token)
        else:
            # У пользователя действительно есть token
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(text="Это безопасно?", callback_data="is_safe")
            kb_builder.adjust(1)

            await message.answer(
                "Привет! Я WB Wizard. Рад снова тебя видеть.\n"
                "Можешь начать работу с /cabinet или настроить в /settings!",
                reply_markup=kb_builder.as_markup()
            )
    else:
        # Если token_id нет - просим прислать токен
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text="Это безопасно?", callback_data="is_safe")
        kb_builder.adjust(1)

        await message.answer(
            "Привет! Я WB Wizard.\n"
            "Чтобы начать, нужно создать API-ключ 🔑\n"
            "Инструкция ниже 👇\n\n"
            "1️⃣ Перейдите в личный кабинет Wildberries\n"
            "2️⃣ Откройте раздел «Доступ к API»\n"
            "3️⃣ Создайте новый ключ и отправьте его сюда\n\n"
            "🛡️ Документы сервиса:\n"
            "• <a href='https://docs.google.com/document/d/15LRh3AoPaXp3CzibhF_uP54L_5aLBLBH/edit?usp=sharing&ouid=114073113894104131349&rtpof=true&sd=true'>Договор оферты</a>\n"
            "• <a href='https://docs.google.com/document/d/1mHECWvSwUoqEb3W4xP_a8pBqUHIQkFzp/edit?usp=sharing&ouid=114073113894104131349&rtpof=true&sd=true'>Политика конфиденциальности</a>\n"
            "• <a href='https://docs.google.com/document/d/1qSEui2LOjZ_0pJ12UwHra9FQh-lkHIMG/edit?usp=sharing&ouid=114073113894104131349&rtpof=true&sd=true'>Согласие на обработку персональных данных</a>\n\n"
            "Отправляя ключ, вы подтверждаете, что ознакомились и принимаете условия оферты, политику конфиденциальности и даёте согласие на обработку персональных данных.",
            reply_markup=kb_builder.as_markup()
        )
        await state.set_state(TokenState.waiting_for_token)

    session.close()

async def callback_is_safe(query: CallbackQuery):
    """
    Когда пользователь жмёт кнопку "Это безопасно?",
    отправляем объяснение про безопасность и функционал.
    """
    await query.message.answer(SAFETY_TEXT, parse_mode="HTML")
    await query.answer()

def register_start_handler(dp: Dispatcher):
    # Регистрируем функцию cmd_start на команду /start
    dp.message.register(cmd_start, Command("start"))
    dp.callback_query.register(callback_is_safe, lambda c: c.data == "is_safe")