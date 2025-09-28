# handlers/tariffs_handler.py
from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.payments import create_payment_for_tariff, refresh_payment_and_activate
from db.database import SessionLocal
from db.models import Token, Payment

BASE_PAYMENT_URL = ""
ADV_PAYMENT_URL  = ""

def _short_alert(text: str, limit: int = 180) -> str:
    return (text[:limit] + "…") if len(text) > limit else text

async def _start_payment(query: types.CallbackQuery, tariff_code: str, label: str):
    res = create_payment_for_tariff(query.from_user.id, tariff_code)
    if not res["ok"]:
        await query.answer(_short_alert("Не удалось создать платеж: " + (res["message"] or "")), show_alert=True)
        return
    url   = res["confirmation_url"]
    pay_id= res["payment_db_id"]
    kb = InlineKeyboardBuilder()
    kb.button(text=f"Оплатить {label}", url=url)
    kb.button(text="Проверить оплату", callback_data=f"checkpay_{pay_id}")
    kb.adjust(1)
    await query.message.answer(f"Перейдите по ссылке для оплаты тарифа «{label}»:", reply_markup=kb.as_markup())

async def cmd_tariffs(message: types.Message):
    text = (
        "<b>Тарифы и преимущества</b>\n\n"

        "1. <b>Free</b> 🆓\n"
        "   • 🛍 Отслеживание заказов, выкупов, отказов и возвратов\n"
        "   • 🏬 Подписка только на 1 склад (бесплатная поставка)\n"
        "   • 🌐 Позиция товара по артикулу и ключевому запросу (1 город)\n"
        "   • 📊 Сводная статистика за 7 дней\n\n"

        "2. <b>Base</b> 🔑 — <b>349 ₽/мес</b>\n"
        "   • Всё из Free, плюс:\n"
        "   • 🚚 Отслеживание заказов и выкупов в реальном времени за 30 дней\n"
        "   • 🏬 До 3 складов (бесплатная поставка)\n"
        "   • 📈 Сводная статистика (Excel) до 30 дней\n\n"

        "3. <b>Advanced</b> 🚀 — <b>949 ₽/мес</b>\n"
        "   • Всё из Base, плюс:\n"
        "   • ⏳ Отслеживание заказов до 90 дней\n"
        "   • 🏬 До 9 складов (бесплатная поставка)\n"
        "   • 🌐 Позиция товара по 20 городам (Excel)\n"
        "   • 📊 Отчёт по позициям с динамикой по городам (Excel)\n"
        "   • 🔑 Ваши ключи и их частотность (Excel)\n"
        "   • 🗺 Контроль остатков по городам (Excel)\n"
        "   • 📑 Сводная статистика до 90 дней\n\n"

        "4. <b>Test</b> 🧪 — функционал уровня Advanced для ознакомления (до 9 складов)\n\n"

        "🔥 <b>Выгодные пакеты</b>\n"
        "   • <b>Base 6 мес</b> — <s>2 094 ₽</s> → <b>1 779,90 ₽</b> (−15%) ≈ 296,65 ₽/мес\n"
        "   • <b>Base 12 мес</b> — <s>4 188 ₽</s> → <b>3 141 ₽</b> (−25%) ≈ 261,75 ₽/мес\n"
        "   • <b>Advanced 6 мес</b> — <s>5 694 ₽</s> → <b>4 839,90 ₽</b> (−15%) ≈ 806,65 ₽/мес\n"
        "   • <b>Advanced 12 мес</b> — <s>11 388 ₽</s> → <b>8 541 ₽</b> (−25%) ≈ 711,75 ₽/мес\n\n"

        "💡 <i>Преимущества пакетов:</i>\n"
        "   • Экономия до <b>25%</b>\n"
        "   • Фиксируем цену на весь срок\n"
        "   • Меньше оплат и забот — вы растёте, мы считаем 📈\n\n"

        "<b>Общее для всех тарифов:</b>\n"
        "   • ✅ Отслеживание бесплатного коэффициента поставки (уведомления)\n"
        "   • ✅ Отслеживание позиций по ключевым запросам\n"
        "   • ✅ Сводная статистика и отчёты в Excel\n"
        "   • ✅ Оповещения почти в реальном времени\n\n"
        "Вопросы — <b>/help</b> 🤝"
    )

    kb = InlineKeyboardBuilder()

    # Base — помесячно и пакеты
    kb.button(text="Base — 349 ₽/мес", callback_data="pay_base")
    kb.button(text="Base 6 мес — 1 779,90 ₽ (−15%)", callback_data="pay_base_6m")
    kb.button(text="Base 12 мес — 3 141 ₽ (−25%)", callback_data="pay_base_12m")

    # Advanced — помесячно и пакеты
    kb.button(text="Advanced — 949 ₽/мес", callback_data="pay_advanced")
    kb.button(text="Advanced 6 мес — 4 839,90 ₽ (−15%)", callback_data="pay_advanced_6m")
    kb.button(text="Advanced 12 мес — 8 541 ₽ (−25%)", callback_data="pay_advanced_12m")

    kb.adjust(1)
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")

# Колбэки
async def callback_pay_base(q: types.CallbackQuery):
    await _start_payment(q, "base", "Base — 349 ₽/мес")

async def callback_pay_advanced(q: types.CallbackQuery):
    await _start_payment(q, "advanced", "Advanced — 949 ₽/мес")

async def callback_pay_base_6m(q: types.CallbackQuery):
    await _start_payment(q, "base_6m", "Base 6 мес — 1 779,90 ₽")

async def callback_pay_base_12m(q: types.CallbackQuery):
    await _start_payment(q, "base_12m", "Base 12 мес — 3 141 ₽")

async def callback_pay_advanced_6m(q: types.CallbackQuery):
    await _start_payment(q, "advanced_6m", "Advanced 6 мес — 4 839,90 ₽")

async def callback_pay_advanced_12m(q: types.CallbackQuery):
    await _start_payment(q, "advanced_12m", "Advanced 12 мес — 8 541 ₽")

async def callback_check_payment(query: types.CallbackQuery):
    data = (query.data or "").strip()
    try:
        payment_db_id = int(data.split("_", 1)[1])
    except Exception:
        await query.answer("Некорректный идентификатор платежа", show_alert=True)
        return

    res = refresh_payment_and_activate(payment_db_id=payment_db_id)
    status = res.get("status")
    msg = res.get("message") or "Статус не получен."

    token_autopay_enabled = None
    session = SessionLocal()
    try:
        pay = session.query(Payment).get(payment_db_id)
        if pay and pay.token_id:
            token = session.query(Token).get(pay.token_id)
            if token:
                token_autopay_enabled = bool(token.autopay_enabled)
    finally:
        session.close()

    auto = "✅ включён" if token_autopay_enabled else "❌ выключен"

    if status == "succeeded":
        until = res.get("token_until")
        role = res.get("role")
        text = (
            "✅ <b>Оплата подтверждена</b>\n"
            f"Тариф: <b>{role}</b>\n"
            f"Подписка действует до: <code>{until}</code>\n"
            f"🔁 Автоплатёж: {auto}\n\n"
            "Изменить: <b>/settings → Автоплатёж</b>"
        )
        kb = InlineKeyboardBuilder()
        kb.button(text="Перейти к настройкам", callback_data="autopay_menu")
        kb.adjust(1)
        await query.message.answer(text, parse_mode="HTML", reply_markup=kb.as_markup())
    elif status == "canceled":
        await query.message.answer("🚫 Оплата отменена. Можете попробовать снова: /tariffs")
    else:
        await query.answer(_short_alert(msg), show_alert=True)

def register_tariffs_handler(dp: Dispatcher):
    dp.message.register(cmd_tariffs, Command("tariffs"))

    dp.callback_query.register(callback_pay_base,             lambda c: c.data == "pay_base")
    dp.callback_query.register(callback_pay_advanced,         lambda c: c.data == "pay_advanced")
    dp.callback_query.register(callback_pay_base_6m,          lambda c: c.data == "pay_base_6m")
    dp.callback_query.register(callback_pay_base_12m,         lambda c: c.data == "pay_base_12m")
    dp.callback_query.register(callback_pay_advanced_6m,      lambda c: c.data == "pay_advanced_6m")
    dp.callback_query.register(callback_pay_advanced_12m,     lambda c: c.data == "pay_advanced_12m")

    dp.callback_query.register(callback_check_payment,        lambda c: c.data and c.data.startswith("checkpay_"))
