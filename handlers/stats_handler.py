from db.models import User
from db.database import SessionLocal
from aiogram import types, Dispatcher
from aiogram.filters import Command

ADMINS = {767173302, 987654321}  # user_id админов
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.answer("У вас нет доступа к статистике.")
        return

    # Получаем кол-во зарегистрированных
    session = SessionLocal()
    total_users = session.query(User).count()

    # Или кол-во, у кого был последний /start за последний месяц и т.д.
    # last_30_days = datetime.utcnow() - timedelta(days=30)
    # active_users = session.query(User).filter(User.last_activity >= last_30_days).count()

    session.close()

    # Выводим
    await message.answer(
        f"<b>Статистика</b>\n"
        f"Всего пользователей: {total_users}\n"
        # f"Активных за 30 дней: {active_users}\n"
        ,
        parse_mode="HTML"
    )

def register_stats_handler(dp: Dispatcher):
    # Регистрируем функцию cmd_start на команду /start
    dp.message.register(cmd_stats, Command("stats"))