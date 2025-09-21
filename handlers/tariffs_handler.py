from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.payments import create_payment_for_tariff, refresh_payment_and_activate  # <-- добавили
from db.database import SessionLocal
from db.models import Token, Payment

# TODO: вставь реальные ссылки, сейчас пусто
BASE_PAYMENT_URL = ""      # например: "https://your-pay.page/base"
ADV_PAYMENT_URL  = ""      # например: "https://your-pay.page/advanced"

async def cmd_tariffs(message: types.Message):
    """
    Выводит информацию по тарифам (free, base, advanced, test) + цены.
    Добавляет кнопки для оплаты Base и Advanced.
    """
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
        "   • 📊 Отчёт по позициям ваших товаров с динамикой по городам (Excel)\n"
        "   • 🔑 Ваши ключи и их частотность (Excel)\n"
        "   • 🗺 Контроль остатков по городам (Excel)\n"
        "   • 📑 Сводная cтатистика до 90 дней\n\n"

        "4. <b>Test</b> 🧪\n"
        "   • Тариф с функционалом уровня Advanced для ознакомления\n"
        "   • 🏬 До 9 складов (бесплатная поставка)\n\n"

        "<b>Общее для всех тарифов:</b>\n"
        "   • ✅ Отслеживание бесплатного коэффициента поставки (уведомления)\n"
        "   • ✅ Отслеживание позиции по ключевому запросу\n"
        "   • ✅ Сводная статистика и отчёты в Excel\n"
        "   • ✅ Оповещения почти в реальном времени\n\n"
        "Если остались вопросы — напишите в <b>/help</b> 🤝"
    )

    kb = InlineKeyboardBuilder()
    if BASE_PAYMENT_URL:
        kb.button(text="Оплатить Base — 349 ₽", url=BASE_PAYMENT_URL)
    else:
        kb.button(text="Оплатить Base — 349 ₽", callback_data="pay_base")

    if ADV_PAYMENT_URL:
        kb.button(text="Оплатить Advanced — 949 ₽", url=ADV_PAYMENT_URL)
    else:
        kb.button(text="Оплатить Advanced — 949 ₽", callback_data="pay_advanced")

    kb.adjust(1)  # по одной кнопке в ряд
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")


# Колбэки на случай, если ссылки ещё не проставлены
async def callback_pay_base(query: types.CallbackQuery):
    # создаем платеж на тариф base
    res = create_payment_for_tariff(query.from_user.id, "base")
    print("Не удалось создать платеж: " + (res["message"] or ""))
    if not res["ok"]:
        await query.answer("Не удалось создать платеж: " + (res["message"] or ""), show_alert=True)
        return
    url = res["confirmation_url"]
    pay_id = res["payment_db_id"]
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить Base — 349 ₽", url=url)
    kb.button(text="Проверить оплату", callback_data=f"checkpay_{pay_id}")
    kb.adjust(1)
    await query.message.answer("Перейдите по ссылке для оплаты тарифа Base:", reply_markup=kb.as_markup())


async def callback_pay_advanced(query: types.CallbackQuery):
    # создаем платеж на тариф advanced
    res = create_payment_for_tariff(query.from_user.id, "advanced")
    if not res["ok"]:
        await query.answer("Не удалось создать платеж: " + (res["message"] or ""), show_alert=True)
        return
    url = res["confirmation_url"]
    pay_id = res["payment_db_id"]
    kb = InlineKeyboardBuilder()
    kb.button(text="Оплатить Advanced — 949 ₽", url=url)
    kb.button(text="Проверить оплату", callback_data=f"checkpay_{pay_id}")
    kb.adjust(1)
    await query.message.answer("Перейдите по ссылке для оплаты тарифа Advanced:", reply_markup=kb.as_markup())

def _short_alert(text: str, limit: int = 180) -> str:
    return (text[:limit] + "…") if len(text) > limit else text

async def callback_check_payment(query: types.CallbackQuery):
    """
    Пользователь нажимает кнопку 'Проверить оплату' после возврата из ЮKassa.
    Формат callback_data: 'checkpay_<payment_db_id>'
    """
    data = (query.data or "").strip()

    # 1) Разбираем payment_db_id
    try:
        payment_db_id = int(data.split("_", 1)[1])
    except Exception:
        await query.answer("Некорректный идентификатор платежа", show_alert=True)
        return

    # 2) Обновляем статус в ЮKassa и БД
    res = refresh_payment_and_activate(payment_db_id=payment_db_id)
    status = res.get("status")
    msg = res.get("message") or "Статус не получен."

    # 3) Достаём автоплатёж по token_id из самой записи Payment
    token_autopay_enabled = None
    try:
        session = SessionLocal()
        pay = session.query(Payment).get(payment_db_id)
        if pay and pay.token_id:
            token = session.query(Token).get(pay.token_id)
            if token:
                token_autopay_enabled = bool(token.autopay_enabled)
    finally:
        try:
            session.close()
        except Exception:
            pass

    auto = "✅ включён" if token_autopay_enabled else "❌ выключен"

    # 4) Отвечаем пользователю
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
        # pending / waiting_for_capture / etc. — короткий алерт
        await query.answer(_short_alert(msg), show_alert=True)
def register_tariffs_handler(dp: Dispatcher):
    dp.message.register(cmd_tariffs, Command("tariffs"))
    dp.callback_query.register(callback_pay_base, lambda c: c.data == "pay_base")
    dp.callback_query.register(callback_pay_advanced, lambda c: c.data == "pay_advanced")
    dp.callback_query.register(callback_check_payment, lambda c: c.data and c.data.startswith("checkpay_"))
