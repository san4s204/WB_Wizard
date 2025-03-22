import datetime
from db.database import SessionLocal
from db.models import User, Token

def user_has_role(session, telegram_id: str, allowed_roles: list[str]) -> bool:
    """
    Универсальная функция проверки доступа:
    1. Ищем User по telegram_id.
    2. Проверяем, есть ли у него token_id.
    3. Берём Token и смотрим token.role.
    4. Если роль = 'super', всегда возвращаем True.
    5. Иначе, если роль входит в allowed_roles, True, иначе False.

    ПРИМЕР использования:
      if user_has_role(session, str(message.from_user.id), ['base','advanced','test']):
          ... # доступ
      else:
          await message.answer('У вас нет доступа.')
    """

    db_user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not db_user or not db_user.token_id:
        return False  # у пользователя нет токена => нет доступа

    token_obj = session.query(Token).filter_by(id=db_user.token_id).first()
    if not token_obj:
        return False  # не нашли сам token => нет доступа

    # Проверяем роль
    role = token_obj.role or "free"  # если не заполнено, считаем 'free'

    # super может всё
    if role == "super":
        return True

    # Иначе проверяем, входит ли роль в список разрешённых
    if role in allowed_roles:
        return True

    return False

def get_user_role(session, db_user) -> str:
    """
    Возвращает роль токена, к которому привязан пользователь (db_user).
    Если нет токена или роль не заполнена – возвращаем 'free'.
    """
    if not db_user.token_id:
        return "free"
    token_obj = session.query(Token).filter_by(id=db_user.token_id).first()
    if not token_obj or not token_obj.role:
        return "free"
    return token_obj.role
