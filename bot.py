import asyncio
from aiogram import Bot, Dispatcher
from config import TELEGRAM_TOKEN
from handlers import register_all_handlers
from aiogram.enums.parse_mode import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand


from utils.logger import logger

from core.scheduler import start_scheduler

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Начать работу с ботом"),
        BotCommand(command="/cabinet", description="Личный кабинет"),
        BotCommand(command="/tariffs", description="Тарифы"),
        BotCommand(command="/my_products", description="Cводный отчёт"),
        BotCommand(command="/positions", description="Позиции"),
        BotCommand(command="/find_positions", description="Позиция товара по артикулу + запросу"),
        BotCommand(command="/report_for_day", description="Еждневный отчёт за прошлую дату"),
        BotCommand(command="/orders", description="Просмотреть список заказов"),
        BotCommand(command="/settings", description="Настройки"),
        BotCommand(command="/help", description="Поддержка"),
        
        
        
    ]
    await bot.set_my_commands(commands)

async def main():
    bot = Bot(
        token=TELEGRAM_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Регистрируем все хендлеры
    register_all_handlers(dp)

    # Запускаем планировщик
    start_scheduler(bot)

    # Устанавливаем команды бота
    await set_commands(bot)

    # Запускаем поллинг (опрос)
    await dp.start_polling(bot)

    # Запускаем лонг поллинг
    logger.info("Какое-то информационное сообщение")
    logger.debug("Более подробное сообщение")
    logger.error("Ошибка!")

if __name__ == "__main__":
    asyncio.run(main())
