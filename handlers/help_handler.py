from aiogram import types, Dispatcher
from aiogram.filters import Command

async def cmd_help(message: types.Message):
    await message.answer("Контакты поддержки: @san4s2034")

def register_help_handler(dp: Dispatcher):
    dp.message.register(cmd_help, Command("help"))
