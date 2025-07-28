from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from states.user_state import user_states
# Предположим, ваша функция поиска:
# from core.search_tracker import find_article_in_search_async



async def cmd_find_position_in_search(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = {"state": "await_article_input"}
    await message.answer(
        "Введите артикул товара (nm_id), например: <code>1234567</code>\n\n"
        "❌ Чтобы выйти из режима поиска — напишите /cancel",
        parse_mode="HTML"
    )



def register_find_position_handlers(dp: Dispatcher):
    """
    Регистрируем наш хендлер в диспатчере Aiogram 3.x
    """
    dp.message.register(cmd_find_position_in_search, Command("find_positions"))
