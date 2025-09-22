# core/cleanup.py
import datetime as dt
from typing import Optional, List
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import Order, Sale, ReportDetails, TrackedPosition

# --- Настройки очистки ---
BATCH_SIZE = 5_000        # сколько строк удаляем за одну транзакцию
MAX_MINUTES = 10          # максимальная длительность одной сессии очистки
MONTHS_TO_KEEP = 6        # хранить N месяцев

def _utcnow() -> dt.datetime:
    return dt.datetime.utcnow()

def _cutoff(months: int = MONTHS_TO_KEEP) -> dt.datetime:
    # стараемся вычесть ровно N месяцев; если relativedelta недоступен — ~6*30 дней
    try:
        from dateutil.relativedelta import relativedelta
        return _utcnow() - relativedelta(months=months)
    except Exception:
        return _utcnow() - dt.timedelta(days=months * 30)

# --- Вспомогалка для парсинга строковых дат в ReportDetails ---
_FMTs = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%d.%m.%Y",
    "%d.%m.%Y %H:%M:%S",
)

def _parse_dt(s: Optional[str]) -> Optional[dt.datetime]:
    if not s:
        return None
    s = s.strip()
    for f in _FMTs:
        try:
            return dt.datetime.strptime(s, f)
        except Exception:
            pass
    # как fallback: попробуем fromisoformat
    try:
        return dt.datetime.fromisoformat(s.replace("Z", ""))
    except Exception:
        return None

# --- Удаление батчами ---
def _delete_by_ids(session: Session, model, ids: List[int]) -> int:
    if not ids:
        return 0
    q = session.query(model).filter(model.id.in_(ids))
    deleted = q.delete(synchronize_session=False)
    session.commit()
    return deleted

def purge_orders(session: Session, cutoff: dt.datetime, batch: int = BATCH_SIZE) -> int:
    total = 0
    while True:
        rows = (
            session.query(Order.id)
            .filter(
                or_(
                    and_(Order.date.isnot(None), Order.date < cutoff),
                    and_(Order.date.is_(None), Order.last_change_date.isnot(None), Order.last_change_date < cutoff),
                )
            )
            .order_by(Order.id)
            .limit(batch)
            .all()
        )
        ids = [r[0] for r in rows]
        if not ids:
            break
        total += _delete_by_ids(session, Order, ids)
        if len(ids) < batch:
            break
    return total

def purge_sales(session: Session, cutoff: dt.datetime, batch: int = BATCH_SIZE) -> int:
    total = 0
    while True:
        rows = (
            session.query(Sale.id)
            .filter(
                or_(
                    and_(Sale.date.isnot(None), Sale.date < cutoff),
                    and_(Sale.date.is_(None), Sale.last_change_date.isnot(None), Sale.last_change_date < cutoff),
                )
            )
            .order_by(Sale.id)
            .limit(batch)
            .all()
        )
        ids = [r[0] for r in rows]
        if not ids:
            break
        total += _delete_by_ids(session, Sale, ids)
        if len(ids) < batch:
            break
    return total

def purge_tracked_positions(session: Session, cutoff: dt.datetime, batch: int = BATCH_SIZE) -> int:
    total = 0
    while True:
        rows = (
            session.query(TrackedPosition.id)
            .filter(TrackedPosition.check_dt.isnot(None), TrackedPosition.check_dt < cutoff)
            .order_by(TrackedPosition.id)
            .limit(batch)
            .all()
        )
        ids = [r[0] for r in rows]
        if not ids:
            break
        total += _delete_by_ids(session, TrackedPosition, ids)
        if len(ids) < batch:
            break
    return total

def purge_report_details(session: Session, cutoff: dt.datetime, batch: int = BATCH_SIZE) -> int:
    """
    В этой таблице даты — строки, поэтому работаем осторожно:
    — берём порции, пытаемся распарсить create_dt/order_dt, удаляем то, что явно старее cutoff.
    Если формат совсем «кривой», запись пропускаем.
    """
    total = 0
    last_id = 0
    while True:
        rows = (
            session.query(ReportDetails.id, ReportDetails.create_dt, ReportDetails.order_dt)
            .filter(ReportDetails.id > last_id)
            .order_by(ReportDetails.id)
            .limit(batch)
            .all()
        )
        if not rows:
            break
        ids_to_delete = []
        for rid, cdt, odt in rows:
            last_id = rid
            d1 = _parse_dt(cdt)
            d2 = _parse_dt(odt)
            # берём наиболее «раннюю» разумную дату строки
            d = None
            if d1 and d2:
                d = min(d1, d2)
            else:
                d = d1 or d2
            if d and d < cutoff:
                ids_to_delete.append(rid)
        if ids_to_delete:
            total += _delete_by_ids(session, ReportDetails, ids_to_delete)
        if len(rows) < batch:
            break
    return total

def purge_old_data(months: int = MONTHS_TO_KEEP, time_limit_minutes: int = MAX_MINUTES) -> dict:
    """
    Основная точка входа (синхронная). Запускается из планировщика в отдельном потоке.
    Возвращает статистику по удалённым строкам.
    """
    started = dt.datetime.utcnow()
    cutoff = _cutoff(months)
    stats = {"orders": 0, "sales": 0, "report_details": 0, "tracked_positions": 0, "cutoff": cutoff.isoformat()}

    with SessionLocal() as session:
        # Orders
        stats["orders"] += purge_orders(session, cutoff)
        if (dt.datetime.utcnow() - started).total_seconds() > time_limit_minutes * 60:
            return stats
        # Sales
        stats["sales"] += purge_sales(session, cutoff)
        if (dt.datetime.utcnow() - started).total_seconds() > time_limit_minutes * 60:
            return stats
        # ReportDetails
        stats["report_details"] += purge_report_details(session, cutoff)
        if (dt.datetime.utcnow() - started).total_seconds() > time_limit_minutes * 60:
            return stats
        # TrackedPosition
        stats["tracked_positions"] += purge_tracked_positions(session, cutoff)

    return stats
