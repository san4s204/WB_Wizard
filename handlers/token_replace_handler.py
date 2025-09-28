# handlers/token_replace_handler.py
import os
import datetime
from aiogram import types, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from sqlalchemy import and_
from db.database import SessionLocal
from db.models import User, Token
from core.wildberries_api import get_seller_info  # sync функция по твоему коду
from utils.logger import logger

DEFAULT_TTL_DAYS = int(os.getenv("WB_TOKEN_DEFAULT_TTL_DAYS", "180"))

class TokenReplaceState(StatesGroup):
    waiting_for_new_token = State()

def _mask(token: str, left: int = 4, right: int = 4) -> str:
    if not token:
        return "—"
    if len(token) <= left + right:
        return token
    return token[:left] + "•" * 6 + token[-right:]

def _human_left(dt_until: datetime.datetime | None) -> str:
    if not dt_until:
        return "не указано"
    now = datetime.datetime.utcnow()
    delta = dt_until - now
    if delta.total_seconds() <= 0:
        return "истёк"
    days = delta.days
    hours = (delta.seconds // 3600)
    return f"{days} дн {hours} ч"

async def cmd_replace_token(message: types.Message, state: FSMContext):
    # стартовая команда
    session = SessionLocal()
    user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
    token = user and user.token
    expires = token and token.token_expires_at
    session.close()

    kb = InlineKeyboardBuilder()
    kb.button(text="Отмена", callback_data="replace_token_cancel")
    kb.adjust(1)

    await message.answer(
        "🔐 <b>Замена токена WB</b>\n\n"
        "Отправьте новый API-токен сообщением (одно сообщение — один токен).\n\n"
        f"Текущий токен: <code>{_mask(token.token_value) if token else '—'}</code>\n"
        f"Срок действия текущего токена: {_human_left(expires)}\n\n"
        "После проверки я обновлю токен без смены подписки и настроек.",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )
    await state.set_state(TokenReplaceState.waiting_for_new_token)

async def callback_replace_token(query: types.CallbackQuery, state: FSMContext):
    # из меню настроек/кабинета
    await query.answer()
    await cmd_replace_token(query.message, state)

async def callback_replace_token_cancel(query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.edit_text("Ок, замена токена отменена.")

async def handle_new_token(message: types.Message, state: FSMContext):
    """
    Пользователь прислал новый токен. Валидируем, обновляем текущий Token.token_value.
    """
    new_token = (message.text or "").strip()
    if not new_token or len(new_token) < 20:
        await message.reply("Похоже, это не токен. Пришлите корректный API-токен WB.")
        return

    # 1) Валидируем на WB API
    try:
        seller = get_seller_info(new_token)  # бросит исключение/вернёт ошибку — будет поймано
        store_name = seller.get("name") or "Магазин"
    except Exception as e:
        logger.error(f"[replace_token] WB check failed: {e}")
        await message.reply("Токен не прошёл проверку на стороне WB. Проверьте и пришлите снова.")
        return

    session = SessionLocal()
    try:
        db_user = session.query(User).filter_by(telegram_id=str(message.from_user.id)).first()
        if not db_user or not db_user.token_id:
            session.close()
            await message.reply("Сначала привяжите токен через /start.")
            await state.clear()
            return

        current_token: Token = session.query(Token).get(db_user.token_id)

        # 2) Проверка на уникальность токена
        exists = session.query(Token).filter(
            and_(Token.token_value == new_token, Token.id != current_token.id)
        ).one_or_none()
        if exists:
            session.close()
            await message.reply("Этот токен уже используется в системе другим аккаунтом. Используйте другой токен.")
            return

        if new_token == current_token.token_value:
            session.close()
            await message.reply("Этот токен совпадает с текущим. Пришлите новый.")
            return

        # 3) Обновляем token_value на месте (без смены token_id)
        current_token.token_value = new_token
        current_token.created_at = datetime.datetime.utcnow()

        # 4) По желанию: выставим срок действия, если хочешь отображать «осталось»
        if DEFAULT_TTL_DAYS > 0:
            current_token.token_expires_at = current_token.created_at + datetime.timedelta(days=DEFAULT_TTL_DAYS)

        # 5) На всякий случай убеждаемся, что токен активен
        current_token.is_active = True

        session.commit()

        await message.reply(
            "✅ Токен обновлён.\n"
            f"Магазин: <b>{store_name}</b>\n"
            f"Токен: <code>{_mask(new_token)}</code>\n"
            f"Срок действия: {_human_left(current_token.token_expires_at)}\n\n"
            "Данные теперь будут подтягиваться по новому токену.",
            parse_mode="HTML"
        )
        await state.clear()
    except Exception as e:
        session.rollback()
        logger.exception(f"[replace_token] save failed: {e}")
        await message.reply("Не удалось обновить токен. Попробуйте позже.")
    finally:
        session.close()

def register_token_replace_handlers(dp: Dispatcher):
    # /replace_token
    dp.message.register(cmd_replace_token, Command("replace_token"))
    # из кнопки
    dp.callback_query.register(callback_replace_token, lambda c: c.data == "replace_token")
    dp.callback_query.register(callback_replace_token_cancel, lambda c: c.data == "replace_token_cancel")
    # приём токена в состоянии
    dp.message.register(handle_new_token, TokenReplaceState.waiting_for_new_token)
