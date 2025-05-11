from aiogram import types, Dispatcher
from aiogram.filters import Command

# Текст, который бот пришлёт по команде /features, /about или /whatcan
# Используем HTML‑разметку (установлена в DefaultBotProperties в bot.py)
FEATURES_MESSAGE: str = (
    "<b>🔮 WB_Wizard — ваш горячий помощник на Wildberries!</b>\n\n"
    "<b>Что он умеет:</b>\n"
    "• 🌍 <b>Мульти‑региональный анализ позиций</b> — проверяет выдачу по ключевым запросам сразу в выбранных городах и присылает удобный Excel‑отчёт.\n"
    "• 🅰️🅱️🅲️ <b>ABC‑анализ</b> — анализирует спрос товара и даёт рекомендации по отгрузке на склады.\n"
    "• 🔔 <b>Автоматические уведомления</b> — сообщает о новых заказах, выкупах и возвратах, чтобы вы не упустили ни одного события.\n"
    "• 📦 <b>Отчёты по остаткам</b> — отображает остатки на всех складах вместе с фото товара, позволяя быстро найти нужный артикул.\n"
    "• 🚀 …и ещё десятки инструментов, которые мы постоянно расширяем!\n\n"
    "Связаться с поддержкой — команда <code>/help</code>."
)


async def cmd_features(message: types.Message) -> None:
    """Ответить описанием возможностей бота."""
    await message.answer(FEATURES_MESSAGE, disable_web_page_preview=True)


def register_features_handler(dp: Dispatcher) -> None:
    """Регистрация хендлера команд /features, /about, /whatcan."""
    dp.message.register(cmd_features, Command("features", "about", "whatcan"))
