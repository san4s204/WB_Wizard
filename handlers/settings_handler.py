# handlers/settings_handler.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from db.database import SessionLocal
from aiogram.filters import Command
from db.models import User, Token
from handlers.free_accept_handler import callback_track_free_accept_menu, callback_track_free_accept_prev, callback_track_free_accept_next, callback_add_wh, callback_del_wh, callback_track_free_accept_coef, callback_add_box, callback_del_box, callback_track_free_accept_box, callback_track_free_accept_coef

from aiogram import Dispatcher

async def cmd_settings_command(message: types.Message):
    """
    Этот хендлер вызовется, когда пользователь напечатает /settings или нажмёт в списке команд
    """
    # Имитируем нажатие коллбэка "settings" — либо просто вызываем ту же логику
    # Из callback_settings(query) нам нужен query.message.edit_text, но сейчас у нас message
    # Можно просто прислать новое сообщение с тем же контентом, что в callback_settings
    # Или создать InlineKeyboardBuilder заново

    kb = InlineKeyboardBuilder()
    kb.button(text="Оповещения🔔", callback_data="notif_menu")
    kb.button(text="Позиции🛍", callback_data="pos_menu")
    kb.button(text="Автоплатёж 💳", callback_data="autopay_menu")
    kb.button(text="Заменить токен 🔐", callback_data="replace_token")
    kb.button(text="Трекинг бесплатной приёмки 🆓🚚", callback_data="track_free_accept_menu")
    kb.button(text="Назад 🔙", callback_data="cabinet")
    kb.adjust(1)

    await message.answer(
        text="Раздел Настройки: выберите пункт",
        reply_markup=kb.as_markup()
    )

async def callback_settings(query: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Оповещения🔔", callback_data="notif_menu")
    kb.button(text="Позиции🛍", callback_data="pos_menu")
    kb.button(text="Автоплатёж 💳", callback_data="autopay_menu")
    kb.button(text="Заменить токен 🔐", callback_data="replace_token")
    kb.button(text="Трекинг бесплатной приёмки 🆓🚚", callback_data="track_free_accept_menu")
    kb.button(text="⬅️Назад", callback_data="cabinet")  # или "cabinet"
    kb.adjust(1)

    await query.message.edit_text(
        text="Раздел Настройки: выберите пункт",
        reply_markup=kb.as_markup()
    )
    await query.answer()

async def callback_notif_menu(query: types.CallbackQuery):
    session = SessionLocal()
    db_user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    if not db_user:
        session.close()
        await query.answer("Пользователь не найден.")
        return
    
    text = f"Настройки оповещений:\n" \
           f"Оповещения по заказам: {'✅' if db_user.notify_orders else '❌'}\n" \
           f"Оповещения по выкупам: {'✅' if db_user.notify_sales else '❌'}\n"  \
           f"Оповещения по поставкам: {'✅' if db_user.notify_incomes else '❌'}\n" \
           f"Ежедневный отчёт: {'✅' if db_user.notify_daily_report else '❌'}"

    kb = InlineKeyboardBuilder()
    kb.button(text=f"Заказы: {'✅' if db_user.notify_orders else '❌'}", callback_data="toggle_orders")
    kb.button(text=f"Выкупы: {'✅' if db_user.notify_sales else '❌'}", callback_data="toggle_sales")
    kb.button(text=f"Поставки: {'✅' if db_user.notify_incomes else '❌'}", callback_data="toggle_incomes")
    kb.button(text=f"Отказы: {'✅' if db_user.notify_cancel else '❌'}", callback_data="toggle_cancel")
    kb.button(text=f"Ежедневный отчёт: {'✅' if db_user.notify_daily_report else '❌'}", callback_data="toggle_daily_report")
    kb.button(text="⬅️Назад", callback_data="settings")
    kb.adjust(1)
    session.close()

    await query.message.edit_text(text, reply_markup=kb.as_markup())
    await query.answer()

async def callback_toggle_orders(query: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    if user:
        user.notify_orders = not user.notify_orders
        session.commit()
    session.close()
    await query.answer("Изменения сохранены!")
    # Перевызываем меню
    await callback_notif_menu(query)

async def callback_toggle_sales(query: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    if user:
        user.notify_sales = not user.notify_sales
        session.commit()
    session.close()
    await query.answer("Изменения сохранены!")
    await callback_notif_menu(query)

async def callback_toggle_cancel(query: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    if user:
        user.notify_cancel = not user.notify_cancel
        session.commit()
    session.close()
    await query.answer("Изменения сохранены!")
    await callback_notif_menu(query)

async def callback_toggle_incomes(query: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    if user:
        user.notify_incomes = not user.notify_incomes
        session.commit()
    session.close()
    await query.answer("Изменения сохранены!")
    await callback_notif_menu(query)

async def callback_toggle_daily_report(query: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    if user:
        user.notify_daily_report = not user.notify_daily_report
        session.commit()
    session.close()
    await query.answer("Изменения сохранены!")
    await callback_notif_menu(query)


async def callback_pos_menu(query: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️Назад", callback_data="settings")
    kb.adjust(1)

    await query.message.edit_text(
        text="Позиции (заглушка)",
        reply_markup=kb.as_markup()
    )
    await query.answer()

async def callback_autopay_menu(query: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    token = session.query(Token).get(getattr(user, "token_id", None)) if user else None
    session.close()

    if not token:
        await query.message.edit_text("Сначала привяжите токен WB в /start.")
        await query.answer()
        return

    status = "✅ Включён" if token.autopay_enabled else "❌ Выключен"
    has_pm = bool(token.yk_payment_method_id)

    text = (
        "🔁 <b>Автоплатёж</b>\n"
        f"Статус: {status}\n"
        f"Способ оплаты: {'✅ сохранён' if has_pm else '❌ не сохранён'}\n\n"
        "• <b>Отменить подписку</b> — автосписания больше не выполняются, доступ действует до конца оплаченного периода.\n"
        "• <b>Отвязать карту</b> — удаляем сохранённый способ оплаты из нашей системы.\n\n"
        "Изменить статус можно здесь или через /settings → Автоплатёж."
    )

    kb = InlineKeyboardBuilder()
    if has_pm:
        kb.button(
            text=("Отключить автоплатёж" if token.autopay_enabled else "Включить автоплатёж"),
            callback_data="toggle_autopay"
        )
        kb.button(text="Отменить подписку", callback_data="cancel_subscription")
        kb.button(text="Отвязать карту", callback_data="unlink_card")
    else:
        kb.button(text="Сохранить способ (оплатить)", callback_data="tariffs_open")
    kb.button(text="⬅️Назад", callback_data="settings")
    kb.adjust(1)

    await query.message.edit_text(text, parse_mode="HTML", reply_markup=kb.as_markup())
    await query.answer()

async def callback_toggle_autopay(query: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    token = session.query(Token).get(getattr(user, "token_id", None)) if user else None
    if not token:
        session.close()
        await query.answer("Сначала привяжите токен WB в /start", show_alert=True)
        return
    if not token.yk_payment_method_id:
        session.close()
        await query.answer("Способ оплаты не сохранён. Проведите оплату через /tariffs.", show_alert=True)
        return
    token.autopay_enabled = not token.autopay_enabled
    session.commit()
    session.close()
    await query.answer("Изменения сохранены!")
    await callback_autopay_menu(query)

async def callback_cancel_subscription(query: types.CallbackQuery):
    # экран подтверждения
    kb = InlineKeyboardBuilder()
    kb.button(text="Да, отменить автосписания", callback_data="cancel_subscription_confirm")
    kb.button(text="⬅️Назад", callback_data="autopay_menu")
    kb.adjust(1)
    await query.message.edit_text(
        "Вы уверены, что хотите <b>отменить подписку</b>? Автосписания будут отключены. "
        "Доступ сохранится до конца оплаченного периода.",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await query.answer()

async def callback_cancel_subscription_confirm(query: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    token = session.query(Token).get(getattr(user, "token_id", None)) if user else None
    if token:
        token.autopay_enabled = False
        session.commit()
    session.close()
    await query.answer("Подписка отменена, автосписания выключены.")
    await callback_autopay_menu(query)

async def callback_unlink_card(query: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="Да, отвязать карту", callback_data="unlink_card_confirm")
    kb.button(text="⬅️Назад", callback_data="autopay_menu")
    kb.adjust(1)
    await query.message.edit_text(
        "Отвязать карту? Мы удалим сохранённый идентификатор способа оплаты.\n"
        "Автосписания также будут отключены.",
        reply_markup=kb.as_markup()
    )
    await query.answer()

async def callback_unlink_card_confirm(query: types.CallbackQuery):
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(query.from_user.id)).first()
    token = session.query(Token).get(getattr(user, "token_id", None)) if user else None
    if token:
        token.autopay_enabled = False
        token.yk_payment_method_id = None
        session.commit()
    session.close()
    await query.answer("Карта отвязана, автосписания выключены.")
    await callback_autopay_menu(query)

def register_settings_handlers(dp: Dispatcher):
    dp.callback_query.register(callback_settings, lambda c: c.data == "settings")
    dp.callback_query.register(callback_notif_menu, lambda c: c.data == "notif_menu")
    dp.callback_query.register(callback_toggle_orders, lambda c: c.data == "toggle_orders")
    dp.callback_query.register(callback_toggle_sales, lambda c: c.data == "toggle_sales")
    dp.callback_query.register(callback_toggle_incomes, lambda c: c.data == "toggle_incomes")
    dp.callback_query.register(callback_toggle_cancel, lambda c: c.data == "toggle_cancel")
    dp.callback_query.register(callback_toggle_daily_report, lambda c: c.data == "toggle_daily_report")
    dp.callback_query.register(callback_pos_menu, lambda c: c.data == "pos_menu")
    dp.callback_query.register(callback_track_free_accept_menu, lambda c: c.data == "track_free_accept_menu")
    dp.callback_query.register(callback_track_free_accept_coef, lambda c: c.data == "track_free_accept_coef")
    dp.callback_query.register(callback_track_free_accept_prev, lambda c: c.data == "track_free_accept_prev")
    dp.callback_query.register(callback_track_free_accept_next, lambda c: c.data == "track_free_accept_next")
    dp.callback_query.register(callback_track_free_accept_box, lambda c: c.data.startswith("track_free_accept_box"))
    dp.callback_query.register(callback_add_box, lambda c: c.data.startswith("add_box_"))
    dp.callback_query.register(callback_del_box, lambda c: c.data.startswith("del_box_"))
    dp.callback_query.register(callback_add_wh, lambda c: c.data.startswith("add_wh_"))
    dp.callback_query.register(callback_del_wh, lambda c: c.data.startswith("del_wh_"))
    dp.callback_query.register(callback_autopay_menu, lambda c: c.data == "autopay_menu")
    dp.callback_query.register(callback_toggle_autopay, lambda c: c.data == "toggle_autopay")
    dp.callback_query.register(callback_cancel_subscription, lambda c: c.data == "cancel_subscription")
    dp.callback_query.register(callback_cancel_subscription_confirm, lambda c: c.data == "cancel_subscription_confirm")
    dp.callback_query.register(callback_unlink_card, lambda c: c.data == "unlink_card")
    dp.callback_query.register(callback_unlink_card_confirm, lambda c: c.data == "unlink_card_confirm")
    dp.message.register(cmd_settings_command, Command("settings"))