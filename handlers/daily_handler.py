# handlers/daily_report.py
import datetime
from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from db.database import SessionLocal
from db.models import User
from utils.notifications import generate_daily_excel_report  # твоя функция из примера

async def cmd_daily_report(message: types.Message):
    """
    /daily_report — вручную сгенерировать и получить ежедневный отчёт
    (последние 24 часа) для текущего пользователя.
    """
    session = SessionLocal()
    try:
        db_user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
        if not db_user or not db_user.token_id:
            await message.answer("Нет привязанного токена. Сначала выполните /start и отправьте ваш API-ключ.")
            return

        await message.answer("Генерирую ежедневный отчёт… это может занять до минуты ⏳")

        # Формируем отчёт (байты Excel)
        report_bytes = await generate_daily_excel_report(db_user.token_id)

        if not report_bytes:
            await message.answer("Не получилось сформировать отчёт: пустой файл.")
            return

        # Отправка документа
        doc = BufferedInputFile(report_bytes, filename=f"daily_report_{datetime.date.today().isoformat()}.xlsx")
        await message.answer_document(
            document=doc,
            caption="Ежедневный отчёт за последние 24 часа 📊"
        )

    except Exception as e:
        await message.answer(f"Ошибка при формировании отчёта: {e}")
    finally:
        session.close()


def register_daily_report_handler(dp: Dispatcher):
    dp.message.register(cmd_daily_report, Command("daily_report"))
