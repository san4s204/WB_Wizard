# payments.py
import os
import uuid
import datetime as dt
import datetime
from decimal import Decimal

from yookassa import Configuration, Payment as YooPayment
from sqlalchemy.orm import Session

# --- ВАЖНО: подстрой импорт моделей/сессии под свой проект ---
# предположим, у тебя есть models.py с User/Token/Payment и db.py с SessionLocal
from db.models import User, Token, Payment
from db.database import SessionLocal  # заменяй путь, если у тебя иначе

# ===== Конфигурация ЮKassa из .env =====
MODE = os.getenv("YOOKASSA_MODE", "prod").lower()
if MODE == "test":
    YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_TEST_SHOP_ID")
    YOOKASSA_API_KEY = os.getenv("YOOKASSA_TEST_API_KEY")
else:
    YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_PROD_SHOP_ID") or os.getenv("YOOKASSA_SHOP_ID")
    YOOKASSA_API_KEY = os.getenv("YOOKASSA_PROD_API_KEY") or os.getenv("YOOKASSA_API_KEY")
YOOKASSA_DEFAULT_CUSTOMER_EMAIL = os.getenv("YOOKASSA_DEFAULT_CUSTOMER_EMAIL", "user@example.com")
YOOKASSA_VAT_CODE = int(os.getenv("YOOKASSA_VAT_CODE", "1"))  # 1=Без НДС (см. доку)
_raw_tax = os.getenv("YOOKASSA_TAX_SYSTEM_CODE")  # 1..6 по 54-ФЗ
YOOKASSA_RETURN_URL_BASE = os.getenv("YOOKASSA_RETURN_URL", "").strip()
YOOKASSA_TAX_SYSTEM_CODE = int(_raw_tax) if _raw_tax and _raw_tax.isdigit() else None

if not (YOOKASSA_API_KEY and YOOKASSA_SHOP_ID):
    raise RuntimeError("Не заданы YOOKASSA_API_KEY / YOOKASSA_SHOP_ID в .env")

Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_API_KEY

# ===== Тарифы =====
TARIFFS = {
    "base": {
        "amount": Decimal("349.00"),
        "days": 30,
        "role": "base",
        "title": "WB Wizard — Base 30d",
    },
    "advanced": {
        "amount": Decimal("949.00"),
        "days": 30,
        "role": "advanced",
        "title": "WB Wizard — Advanced 30d",
    },
}

def _now_utc() -> dt.datetime:
    return dt.datetime.utcnow()

def _fmt_amount(dec: Decimal) -> str:
    # ЮKassa требует строку с двумя знаками после запятой
    return f"{dec:.2f}"

def _ensure_user_and_token(session: Session, tg_id: str) -> tuple[User, Token]:
    user = session.query(User).filter(User.telegram_id == str(tg_id)).one_or_none()
    if user is None:
        user = User(telegram_id=str(tg_id))
        session.add(user)
        session.flush()

    token = None
    if user.token_id:
        token = session.query(Token).get(user.token_id)

    if token is None:
        token = Token(
            token_value=uuid.uuid4().hex,
            role="free",
            is_active=True,
        )
        session.add(token)
        session.flush()
        user.token_id = token.id
        session.flush()

    return user, token

def _apply_subscription(session: Session, token: Token, tariff_code: str):
    """
    Применяет подписку к токену (продлевает на X дней согласно тарифу).
    """
    cfg = TARIFFS[tariff_code]
    now = _now_utc()
    start_from = token.subscription_until if token.subscription_until and token.subscription_until > now else now
    new_until = start_from + dt.timedelta(days=cfg["days"])

    token.subscription_until = new_until
    token.role = cfg["role"]
    token.is_active = True

def _payment_return_url(payment_db_id: int | None, yk_payment_id: str | None) -> str | None:
    """
    Возвращаем deep-link с идентификатором оплаты (чтобы по /start легко проверить и активировать).
    Если в .env уже стоит '?start=paid', мы аккуратно добавим суффикс.
    Примеры:
      base: https://t.me/WB_Wizard_bot?start=paid_123
      или    https://t.me/WB_Wizard_bot?start=paid_2f3d... (yk id)
    """
    if not YOOKASSA_RETURN_URL_BASE:
        return None
    suffix = ""
    if payment_db_id:
        suffix = f"_{payment_db_id}"
    elif yk_payment_id:
        suffix = f"_{yk_payment_id}"
    # если URL уже содержит ?start=paid — просто доклеим суффикс
    if YOOKASSA_RETURN_URL_BASE.endswith("start=paid"):
        return YOOKASSA_RETURN_URL_BASE + suffix
    # иначе вернем как есть
    return YOOKASSA_RETURN_URL_BASE

def create_payment_for_tariff(tg_user_id: str, tariff_code: str) -> dict:
    """
    Создает платеж в ЮKassa и запись в БД со статусом pending.
    Возвращает dict: {
        "ok": bool,
        "message": str,
        "confirmation_url": str | None,
        "payment_db_id": int | None,
        "yk_payment_id": str | None
    }
    """
    if tariff_code not in TARIFFS:
        return {"ok": False, "message": f"Неизвестный тариф: {tariff_code}", "confirmation_url": None,
                "payment_db_id": None, "yk_payment_id": None}

    cfg = TARIFFS[tariff_code]

    with SessionLocal() as session:
        user, token = _ensure_user_and_token(session, str(tg_user_id))

        token.autopay_merchant_customer_id = token.autopay_merchant_customer_id or str(user.telegram_id or user.id)
        session.flush()

        # 1) Создаем запись в БД (pending)
        pay_db = Payment(
            user_id=user.id,
            token_id=token.id,
            tariff=tariff_code,
            amount=cfg["amount"],
            currency="RUB",
            yk_payment_id="",
            status="pending",
            description=cfg["title"],
        )
        session.add(pay_db)
        session.flush()  # чтобы получить pay_db.id

        # 2) Создаем платеж в ЮKassa
        idem_key = str(uuid.uuid4())

        receipt = {
            "customer": {
                # По правилам ЮKassa чек отправляют на e-mail, см. доку
                "email": YOOKASSA_DEFAULT_CUSTOMER_EMAIL
            },
            "items": [
                {
                    "description": cfg["title"],           # например: "WB Wizard — Base 30d"
                    "quantity": 1.0,                       # число, до 3 знаков после запятой
                    "amount": {
                        "value": _fmt_amount(cfg["amount"]),
                        "currency": "RUB"
                    },
                    "vat_code": YOOKASSA_VAT_CODE,         # 1=без НДС; если нужен 20% — 4
                    "payment_mode": "full_prepayment",     # предоплата за подписку
                    "payment_subject": "service"           # мы продаём услугу
                }
            ]
        }

        if YOOKASSA_TAX_SYSTEM_CODE:
            receipt["tax_system_code"] = YOOKASSA_TAX_SYSTEM_CODE  # 1..6, если требуется

        yk_payload = {
            "amount": {"value": _fmt_amount(cfg["amount"]), "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": _payment_return_url(pay_db.id, None) or "https://yookassa.ru/",
            },
            "capture": True,  # автокапчур — после оплаты статус перейдет в 'succeeded'
            "description": cfg["title"],
            "metadata": {
                "payment_db_id": pay_db.id,
                "user_id": user.id,
                "token_id": token.id,
                "tariff": tariff_code,
            },
            "receipt": receipt,

            "save_payment_method": True,                         # сохранить способ оплаты
            "merchant_customer_id": token.autopay_merchant_customer_id,
        }

        try:
            yk = YooPayment.create(yk_payload, idem_key)
        except Exception as e:
            session.rollback()
            return {"ok": False, "message": f"Ошибка ЮKassa: {e}", "confirmation_url": None,
                    "payment_db_id": None, "yk_payment_id": None}

        pay_db.yk_payment_id = yk.id
        pay_db.status = yk.status or "pending"
        session.commit()

        confirmation_url = getattr(yk.confirmation, "confirmation_url", None)
        return {
            "ok": True,
            "message": "Платеж создан",
            "confirmation_url": confirmation_url,
            "payment_db_id": pay_db.id,
            "yk_payment_id": yk.id,
        }

def refresh_payment_and_activate(payment_db_id: int | None = None, yk_payment_id: str | None = None) -> dict:
    """
    Подтягивает статус платежа из ЮKassa. Если 'succeeded' — активирует подписку на токене.
    Возвращает dict: {ok, status, message, token_until, role}
    """
    if not payment_db_id and not yk_payment_id:
        return {"ok": False, "status": None, "message": "Не передан идентификатор платежа", "token_until": None, "role": None}

    with SessionLocal() as session:
        # 1) Находим платеж в БД
        pay_q = session.query(Payment)
        if payment_db_id:
            pay_db = pay_q.filter(Payment.id == payment_db_id).one_or_none()
        else:
            pay_db = pay_q.filter(Payment.yk_payment_id == str(yk_payment_id)).one_or_none()

        if not pay_db:
            return {"ok": False, "status": None, "message": "Платеж не найден", "token_until": None, "role": None}

        # Если уже активирован
        if pay_db.status == "succeeded":
            token = session.query(Token).get(pay_db.token_id) if pay_db.token_id else None
            return {"ok": True, "status": "succeeded", "message": "Подписка уже активна",
                    "token_until": getattr(token, "subscription_until", None),
                    "role": getattr(token, "role", None)}

        # 2) Запрашиваем у ЮKassa
        try:
            yk = YooPayment.find_one(pay_db.yk_payment_id)
        except Exception as e:
            return {"ok": False, "status": None, "message": f"Ошибка запроса статуса ЮKassa: {e}",
                    "token_until": None, "role": None}

        pay_db.status = yk.status or pay_db.status

        if yk.status == "succeeded":
            # активируем подписку на токене
            token = session.query(Token).get(pay_db.token_id) if pay_db.token_id else None
            if token is None:
                session.commit()
                return {"ok": False, "status": yk.status, "message": "Token не найден для платежа",
                        "token_until": None, "role": None}
            try:
                pm = getattr(yk, "payment_method", None)
                if pm and getattr(pm, "saved", False) and getattr(pm, "id", None):
                    token.yk_payment_method_id = pm.id   # важный момент
                    # автоплатёж по умолчанию НЕ включаем — включает сам пользователь
            except Exception:
                pass

            _apply_subscription(session, token, pay_db.tariff)

            # по желанию — синхронизируем срок и в User (если нужно)
            user = session.query(User).get(pay_db.user_id)
            if user:
                user.subscription_until = token.subscription_until

            session.commit()
            return {"ok": True, "status": "succeeded", "message": "Оплата получена. Подписка активирована.",
                    "token_until": token.subscription_until, "role": token.role}

        elif yk.status == "canceled":
            session.commit()
            return {"ok": False, "status": "canceled", "message": "Оплата отменена.",
                    "token_until": None, "role": None}
        else:
            session.commit()
            return {"ok": True, "status": yk.status, "message": "Платеж еще не завершен.",
                    "token_until": None, "role": None}

def create_recurring_payment(token_id: int, tariff_code: str, parent_payment_id: int | None = None) -> dict:
    """
    Создаёт повторный платёж по сохранённому способу (без редиректа).
    """
    if tariff_code not in TARIFFS:
        return {"ok": False, "message": "Неизвестный тариф", "yk_payment_id": None, "status": None}

    cfg = TARIFFS[tariff_code]

    with SessionLocal() as session:
        token = session.query(Token).get(token_id)
        if not token or not token.yk_payment_method_id:
            return {"ok": False, "message": "Способ оплаты не сохранён", "yk_payment_id": None, "status": None}

        user = session.query(User).filter(User.id == session.query(User.id).filter(User.token_id == token_id).scalar()).one_or_none()
        if not user:
            user = session.query(User).filter(User.token_id == token_id).one_or_none()

        pay_db = Payment(
            user_id=getattr(user, "id", None),
            token_id=token.id,
            tariff=tariff_code,
            amount=cfg["amount"],
            currency="RUB",
            yk_payment_id="",
            status="pending",
            description=f"{cfg['title']} (recurring)",
            is_recurring=True,
            yk_payment_method_id=token.yk_payment_method_id,
            parent_payment_id=parent_payment_id
        )
        session.add(pay_db)
        session.flush()

        receipt = {
            "customer": {"email": YOOKASSA_DEFAULT_CUSTOMER_EMAIL},
            "items": [{
                "description": cfg["title"],
                "quantity": 1.0,
                "amount": {"value": _fmt_amount(cfg["amount"]), "currency": "RUB"},
                "vat_code": YOOKASSA_VAT_CODE,
                "payment_mode": "full_prepayment",
                "payment_subject": "service",
            }]
        }
        if YOOKASSA_TAX_SYSTEM_CODE:
            receipt["tax_system_code"] = YOOKASSA_TAX_SYSTEM_CODE

        idem_key = str(uuid.uuid4())
        yk_payload = {
            "amount": {"value": _fmt_amount(cfg["amount"]), "currency": "RUB"},
            "capture": True,
            "description": pay_db.description,
            "metadata": {"payment_db_id": pay_db.id, "token_id": token.id, "tariff": tariff_code, "recurring": True},
            "payment_method_id": token.yk_payment_method_id,  # <<< главное поле
            "merchant_customer_id": token.autopay_merchant_customer_id,
            "receipt": receipt,
        }

        try:
            yk = YooPayment.create(yk_payload, idem_key)  # без confirmation
        except Exception as e:
            session.rollback()
            return {"ok": False, "message": f"Ошибка ЮKassa: {e}", "yk_payment_id": None, "status": None}

        pay_db.yk_payment_id = yk.id
        pay_db.status = yk.status or "pending"

        if yk.status == "succeeded":
            _apply_subscription(session, token, tariff_code)
            # запланируем следующую дату автосписания (через 30 дней)
            token.autopay_last_charge_at = _now_utc()
            token.autopay_next_charge_at = (token.autopay_last_charge_at + datetime.timedelta(days=cfg["days"]))
            token.autopay_fail_count = 0

        elif yk.status == "canceled":
            token.autopay_fail_count = (token.autopay_fail_count or 0) + 1

        session.commit()
        return {"ok": True, "message": "Создан платёж", "yk_payment_id": yk.id, "status": yk.status}