# core/fill_logistic_tariffs.py
import datetime
from typing import List

from db.database        import SessionLocal
from db.models          import LogisticTariff, Token
from utils.token_utils  import get_active_tokens
from core.wildberries_api import get_tariffs_for_date   # async get_tariffs(kind, date, token)

from sqlalchemy import update, select
import asyncio
import logging

logger = logging.getLogger(__name__)


async def _fetch_all_tariffs(date_: datetime.date, token: str) -> List[dict]:
    out: list[dict] = []

    # box
    for row in await get_tariffs_for_date(token, "box", date_.isoformat()):
        out.append({
            "warehouseName": row["warehouseName"],
            "boxTypeId"   : row["boxTypeId"],
            "boxTypeName" : row["boxTypeName"],
            "tariffRub"   : float(str(row["tariff"]).replace(",", "."))
        })

    # pallet
    for row in await get_tariffs_for_date(token, "pallet", date_.isoformat()):
        out.append({
            "warehouseName": row["warehouseName"],
            "boxTypeId"   : row["boxTypeId"],
            "boxTypeName" : row["boxTypeName"],
            "tariffRub"   : float(str(row["tariff"]).replace(",", "."))
        })

    return out


async def refresh_logistic_tariffs() -> None:
    """
    Обновляем таблицу LogisticTariff на «сегодня».
    • Берём *любой* активный WB-токен (нам нужен лишь доступ к API).
    • Box- и pallet-тарифы запрашиваются по /api/v1/tariffs/…
    • Для каждой (warehouse, boxTypeId) делаем UPSERT.
    """

    # ---------- 1) выбираем токен ----------
    session = SessionLocal()
    tokens = get_active_tokens(session)
    if not tokens:
        logger.warning("[tariffs] нет активных токенов – пропускаю обновление")
        session.close()
        return

    token_value = tokens[0].token_value          # одного токена достаточно
    today       = datetime.date.today()

    # ---------- 2) получаем тарифы ----------
    rows = await _fetch_all_tariffs(today, token_value)
    if not rows:
        logger.warning("[tariffs] API вернул пустой список")
        session.close()
        return

    # ---------- 3) upsert ----------
    new_, upd_ = 0, 0
    for row in rows:
        stmt = (
            update(LogisticTariff)
            .where(LogisticTariff.warehouse_id == row["warehouseName"],
                   LogisticTariff.box_type_id    == row["boxTypeId"])
            .values(
                box_type_name = row["boxTypeName"],
                tariff_rub    = row["tariffRub"],
                updated_at    = datetime.datetime.utcnow()
            )
            .execution_options(synchronize_session=False)
        )
        res = session.execute(stmt)
        if res.rowcount == 0:            # не было записи – вставляем
            session.add(LogisticTariff(
                warehouse_id   = row["warehouseName"],
                box_type_id    = row["boxTypeId"],
                box_type_name  = row["boxTypeName"],
                tariff_rub     = row["tariffRub"],
                updated_at     = datetime.datetime.utcnow()
            ))
            new_ += 1
        else:
            upd_ += 1

    session.commit()
    session.close()
    logger.info(f"[tariffs] inserted {new_} / updated {upd_}")
