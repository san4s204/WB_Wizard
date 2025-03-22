from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import Dispatcher

# Предположим, у вас есть уже написанные хендлеры в других файлах:
from .orders_handler import cmd_orders
from .report_handler import cmd_my_products
from .help_handler import cmd_help
from .cabinet_handler import cmd_cabinet
# Универсальный подход: один хендлер на несколько callback_data
async def callback_cabinet_menu(query: CallbackQuery):
    """
    Универсальный callback-хендлер для кнопок "orders", "my_products", "help", "settings".
    В зависимости от query.data вызываем соответствующую логику.
    """
    user_id = query.from_user.id  # объявляем в начале функции

    if query.data == "orders":
        # Показываем выбор периодов 7, 30, 90
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="7 дней", callback_data="orders 7")],
                [InlineKeyboardButton(text="30 дней", callback_data="orders 30")],
                [InlineKeyboardButton(text="90 дней", callback_data="orders 90")]
            ]
        )
        await query.message.answer("За какой период вывести заказы?", reply_markup=kb)

    elif query.data in ("orders 7", "orders 30", "orders 90"):
        # Извлекаем период из callback_data
        days_str = query.data.split()[1]  # в виде '7', '30', '90'
        days = int(days_str)
        await cmd_orders(query.message, user_id, days=days)
        await query.message.delete() # Удаляем сообщение с кнопками
    elif query.data == "my_products":
        # Показываем выбор периодов 7, 30, 90
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="7 дней", callback_data="my_products_7")],
                [InlineKeyboardButton(text="30 дней", callback_data="my_products_30")],
                [InlineKeyboardButton(text="90 дней", callback_data="my_products_90")]
            ]
        )
        await query.message.answer("За какой период вывести отчёт?", reply_markup=kb)

    elif query.data in ("my_products_7", "my_products_30", "my_products_90"):
        # Извлекаем период из callback_data
        days_str = query.data.split("_")[2]  # в виде '7', '30', '90'
        print(days_str)
        days = int(days_str)
        await cmd_my_products(query.message, user_id, days=days)
        await query.message.delete()  # Удаляем сообщение с кнопками

    elif query.data == "help":
        # Логика "Поддержка"
        await cmd_help(query.message)
    elif query.data == "cabinet":
        # Логика "Личный кабинет"
        await cmd_cabinet(query.message, user_id)
    # Обязательно подтверждаем callback, чтобы Telegram не висел
    await query.answer()

def register_callback_handlers(dp: Dispatcher):
    """
    Функция, регистрирующая все наши callback-хендлеры в диспатчере.
    """
    # Регистрируем универсальный хендлер
    dp.callback_query.register(callback_cabinet_menu, lambda c: c.data in {
        "orders", "my_products", "help", "cabinet", "my_products_7", "my_products_30", "my_products_90",
        "orders 7", "orders 30", "orders 90"
        })
