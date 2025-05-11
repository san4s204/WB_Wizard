from db.models import Token
from db.database import SessionLocal
from sqlalchemy.orm import Session

def get_active_tokens(session: Session | None = None) -> list[Token]:
    """
    Вернуть список только активных токенов.
    Не передавать сессию — создаётся и закрывается локально.
    """
    local = False
    if session is None:
        session = SessionLocal()
        local = True

    tokens = session.query(Token).filter_by(is_active=True).all()

    if local:
        session.close()
    return tokens
