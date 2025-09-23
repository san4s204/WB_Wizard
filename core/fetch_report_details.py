import datetime
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import ReportDetails, Token
from core.wildberries_api import fetch_full_report
from utils.token_utils import get_active_tokens
import logging

logger = logging.getLogger(__name__)

async def save_report_details():
    """
    Сохраняет данные из API Wildberries в таблицу `report_details` для всех токенов.
    """
    session = SessionLocal()

    try:
        tokens_list = get_active_tokens(session)
        if not tokens_list:
            logger.info("[report_details] Активных токенов нет — выходим.")
            return
       

        # 2) Для каждого токена качаем отчёт за нужный период, сохраняем
        period_days = 30
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=period_days)
        date_from_str = start_date.isoformat()
        date_to_str = end_date.isoformat()

        total_inserted = 0
        total_skipped = 0

        for token_obj in tokens_list:
            user_token = token_obj.token_value

            # 3) Запрашиваем данные из API
            report_data = await fetch_full_report(date_from_str, date_to_str, user_token)
            if not report_data:
                print(f"Нет данных для token_id={token_obj.id} ({user_token})")
                continue

            count_inserted_this_token = 0
            count_skipped_this_token = 0

            for entry in report_data:

                # Создаём объект ReportDetails, включая token_id
                report_detail = ReportDetails(
                    create_dt=entry["create_dt"],
                    nm_id=entry["nm_id"],
                    office_name=entry["office_name"],
                    order_dt=entry["order_dt"],
                    commission_percent=entry["commission_percent"],
                    report_type=entry["report_type"]
                )
                session.add(report_detail)
                count_inserted_this_token += 1

            session.commit()

            total_inserted += count_inserted_this_token
            total_skipped += count_skipped_this_token

            print(
                f"Token {token_obj.id}: добавлено {count_inserted_this_token}, "
                f"пропущено {count_skipped_this_token}"
            )

        session.close()
        print(f"[ИТОГО] Добавлено {total_inserted} записей, пропущено {total_skipped}")
    finally:
        session.close()