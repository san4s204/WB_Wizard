# start_handler.py
from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import CallbackQuery
from db.database import SessionLocal
from db.models import User, Token
from states.token_state import TokenState
from core.payments import refresh_payment_and_activate

WB_API_INTEGRATIONS_URL = "https://seller.wildberries.ru/api-integrations"  # ← добавили

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
    # ---- БЛОК deep-link: /start paid_123 ----
    txt = message.text or ""
    arg = ""
    parts = txt.split(maxsplit=1)
    if len(parts) > 1:
        arg = parts[1].strip()

    if arg.startswith("paid"):
        payment_db_id = None
        if "_" in arg:
            tail = arg.split("_", 1)[1]
            if tail.isdigit():
                payment_db_id = int(tail)

        res = refresh_payment_and_activate(payment_db_id=payment_db_id)
        status = res.get("status")
        if status == "succeeded":
            until = res.get("token_until")
            role = res.get("role")
            await message.answer(
                "✅ Оплата подтверждена!\n"
                f"Тариф: <b>{role}</b>\n"
                f"Действует до: <code>{until}</code>\n\n"
                "Команды: /help /tariffs",
                parse_mode="HTML"
            )
            return
        elif status == "canceled":
            await message.answer("🚫 Оплата отменена. Попробуйте снова: /tariffs")
            return
        else:
            await message.answer("Платёж ещё обрабатывается. Вернись к сообщению с кнопкой «Проверить оплату» или открой /tariffs.")
            return
    # ---- конец блока deep-link ----

    await message.delete()

    session = SessionLocal()
    db_user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()

    if not db_user:
        db_user = User(telegram_id=str(message.from_user.id), subscription_until=None, token_id=None)
        session.add(db_user)
        session.commit()

    if db_user.token_id is not None:
        token_obj = session.query(Token).get(db_user.token_id)
        kb_builder = InlineKeyboardBuilder()
        # ↓↓↓ новая кнопка ссылкой на создание токена
        kb_builder.button(text="Создать API-ключ 🔑", url=WB_API_INTEGRATIONS_URL)
        kb_builder.button(text="Это безопасно?", callback_data="is_safe")
        kb_builder.adjust(1)

        if token_obj is None:
            db_user.token_id = None
            session.commit()
            await message.answer(
                "У вас не найден валидный токен. Пожалуйста, создайте новый API-ключ и пришлите его сюда.",
                reply_markup=kb_builder.as_markup()
            )
            await state.set_state(TokenState.waiting_for_token)
        else:
            await message.answer(
                "Привет! Я WB Wizard. Рад снова тебя видеть.\n"
                "Можешь начать работу с /cabinet или настроить в /settings!\n\n"
                "Если нужно, можешь сгенерировать новый API-ключ кнопкой ниже.",
                reply_markup=kb_builder.as_markup()
            )
    else:
        # Нет токена — просим создать и прислать
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text="Создать API-ключ 🔑", url=WB_API_INTEGRATIONS_URL)  # ← новая кнопка
        kb_builder.button(text="Это безопасно?", callback_data="is_safe")
        kb_builder.adjust(1)

        await message.answer(
            "Привет! Я WB Wizard.\n"
            "Чтобы начать, нужно создать API-ключ 🔑\n"
            "Можно перейти по кнопке ниже или выполнить шаги из инструкции:\n\n"
            "1️⃣ Перейдите в личный кабинет Wildberries\n"
            "2️⃣ Откройте раздел «Доступ к API»\n"
            "3️⃣ Выберите разделы: Контент, Аналитика, Возвраты, Статистика, Финансы, Поставки\n"
            "4️⃣ Создайте новый ключ и отправьте его сюда\n\n"
            "🛡️ Документы сервиса:\n"
            "• <a href='https://docs.google.com/document/d/15LRh3AoPaXp3CzibhF_uP54L_5aLBLBH/edit?usp=sharing&ouid=114073113894104131349&rtpof=true&sd=true'>Договор оферты</a>\n"
            "• <a href='https://docs.google.com/document/d/1mHECWvSwUoqEb3W4xP_a8pBqUHIQkFzp/edit?usp=sharing&ouid=114073113894104131349&rtpof=true&sd=true'>Политика конфиденциальности</a>\n"
            "• <a href='https://docs.google.com/document/d/1qSEui2LOjZ_0pJ12UwHra9FQh-lkHIMG/edit?usp=sharing&ouid=114073113894104131349&rtpof=true&sd=true'>Согласие на обработку персональных данных</a>\n\n"
            "Отправляя ключ, вы подтверждаете, что ознакомились и принимаете условия оферты, политику конфиденциальности и даёте согласие на обработку персональных данных.",
            reply_markup=kb_builder.as_markup(),
            parse_mode="HTML"
        )
        await state.set_state(TokenState.waiting_for_token)

    session.close()

async def callback_is_safe(query: CallbackQuery):
    await query.message.answer(SAFETY_TEXT, parse_mode="HTML")
    await query.answer()

def register_start_handler(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.callback_query.register(callback_is_safe, lambda c: c.data == "is_safe")
