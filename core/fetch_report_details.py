import datetime
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import ReportDetails, Token
from core.wildberries_api import fetch_full_report

async def save_report_details():
    """
    Сохраняет данные из API Wildberries в таблицу `report_details` для всех токенов.
    """
    session = SessionLocal()

    # 1) Идём по всем токенам
    all_tokens = session.query(Token).all()

    # 2) Для каждого токена качаем отчёт за нужный период, сохраняем
    period_days = 30
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=period_days)
    date_from_str = start_date.isoformat()
    date_to_str = end_date.isoformat()

    total_inserted = 0
    total_skipped = 0

    for token_obj in all_tokens:
        user_token = token_obj.token_value

        # 3) Запрашиваем данные из API
        report_data = await fetch_full_report(date_from_str, date_to_str, user_token)
        if not report_data:
            print(f"Нет данных для token_id={token_obj.id} ({user_token})")
            continue

        count_inserted_this_token = 0
        count_skipped_this_token = 0

        for entry in report_data:
            subject_name = (entry.get("subject_name") or "").strip()
            if not subject_name:
                count_skipped_this_token += 1
                continue

            # Создаём объект ReportDetails, включая token_id
            report_detail = ReportDetails(
                create_dt=entry["create_dt"],
                subject_name=subject_name,
                nm_id=entry["nm_id"],
                brand_name=entry["brand_name"],
                quantity=entry["quantity"],
                retail_price=entry["retail_price"],
                retail_amount=entry["retail_amount"],
                office_name=entry["office_name"],
                order_dt=entry["order_dt"],
                delivery_amount=entry["delivery_amount"],
                return_amount=entry["return_amount"],
                delivery_rub=entry["delivery_rub"],
                commission_percent=entry["commission_percent"],
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
