from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
        "   • 🔑 Ваши ключи и их частотность (Excel)\n"
        "   • 🗺 Контроль остатков по городам (Excel)\n"
        "   • 📑 Сводная инфа сразу в нескольких Excel-таблицах\n\n"

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
    if BASE_PAYMENT_URL:
        await query.message.answer(f"Оплата Base: {BASE_PAYMENT_URL}")
    else:
        await query.answer("Ссылка на оплату тарифа Base появится скоро 🙌", show_alert=True)

async def callback_pay_advanced(query: types.CallbackQuery):
    if ADV_PAYMENT_URL:
        await query.message.answer(f"Оплата Advanced: {ADV_PAYMENT_URL}")
    else:
        await query.answer("Ссылка на оплату тарифа Advanced появится скоро 🚀", show_alert=True)


def register_tariffs_handler(dp: Dispatcher):
    dp.message.register(cmd_tariffs, Command("tariffs"))
    dp.callback_query.register(callback_pay_base, lambda c: c.data == "pay_base")
    dp.callback_query.register(callback_pay_advanced, lambda c: c.data == "pay_advanced")
