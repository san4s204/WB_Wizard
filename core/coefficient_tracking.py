import datetime
from db.database import SessionLocal
from db.models import AcceptanceCoefficient, Token
from core.wildberries_api import get_acceptance_coefficients

async def check_acceptance_coeffs():
    """
    Опрос /acceptance/coefficients,
    сохраняем новые/обновлённые записи в БД AcceptanceCoefficient.
    Возвращаем список словарей (например, для уведомлений).
    """
    print("Начали проверку коэффициентов приёмки")
    session = SessionLocal()

    tokens_list = session.query(Token).all()
    all_new_coeffs = []

    for token_obj in tokens_list:
        token_id = token_obj.id
        token_value = token_obj.token_value

        data_list = await get_acceptance_coefficients(token_value)
        if not data_list:
            continue

        for data in data_list:
            # Парсим даты и числа
            date_str = data.get("date")  # '2025-03-12T00:00:00Z'
            date_obj = parse_datetime_z(date_str)  # ваша функция для fromisoformat + 'Z'

            # Преобразуем строковые поля с запятой в float
            delivery_base_liter = parse_float_wb(data.get("deliveryBaseLiter"))
            delivery_additional_liter = parse_float_wb(data.get("deliveryAdditionalLiter"))
            storage_base_liter = parse_float_wb(data.get("storageBaseLiter"))
            storage_additional_liter = parse_float_wb(data.get("storageAdditionalLiter"))

            wh_id = data.get("warehouseID")
            box_id = data.get("boxTypeID")

            # Пытаемся найти запись
            existing = (session.query(AcceptanceCoefficient)
                .filter_by(
                    token_id=token_id,
                    warehouse_id=wh_id,
                    date=date_obj,
                    box_type_id=box_id
                ).first())

            if not existing:
                # Создаём новую
                new_coeff = AcceptanceCoefficient(
                    token_id=token_id,
                    date=date_obj,
                    coefficient=data.get("coefficient", 0),
                    warehouse_id=wh_id,
                    warehouse_name=data.get("warehouseName", ""),
                    allow_unload=data.get("allowUnload", False),
                    box_type_name=data.get("boxTypeName", ""),
                    box_type_id=box_id,
                    storage_coef=parse_float_or_none(data.get("storageCoef")),
                    delivery_coef=parse_float_or_none(data.get("deliveryCoef")),
                    delivery_base_liter=delivery_base_liter,
                    delivery_additional_liter=delivery_additional_liter,
                    storage_base_liter=storage_base_liter,
                    storage_additional_liter=storage_additional_liter,
                    is_sorting_center=data.get("isSortingCenter", False)
                )
                session.add(new_coeff)
                session.commit()

                all_new_coeffs.append({
                    "token_id": token_id,
                    "date": date_obj.isoformat() if date_obj else None,
                    "warehouse_name": new_coeff.warehouse_name,
                    "coefficient": new_coeff.coefficient,
                    "box_type_name": new_coeff.box_type_name
                })
            else:
                # Проверяем, нужно ли обновить coefficient, allowUnload, etc.
                # Если поменялось - обновляем
                updated = False
                new_coeff_value = data.get("coefficient", 0)
                if new_coeff_value != existing.coefficient:
                    # Обновляем коэффициент
                    print(f"Обновляем коэффициент {existing.warehouse_name} {existing.box_type_name} ({existing.coefficient} -> {new_coeff_value})")
                    existing.coefficient = new_coeff_value
                    updated = True

                new_allow = data.get("allowUnload", existing.allow_unload)
                if new_allow != existing.allow_unload:
                    print(f"Обновляем доступность приёмки {existing.warehouse_name} ({existing.allow_unload} -> {new_allow})")
                    existing.allow_unload = new_allow
                    updated = True

                # ... и так далее, если хотите проверять warehouseName, etc.

                if updated:
                    session.commit()
                    all_new_coeffs.append({
                        "token_id": token_id,
                        "date": date_obj.isoformat() if date_obj else None,
                        "warehouse_id": existing.warehouse_id,
                        "warehouse_name": existing.warehouse_name,
                        "coefficient": existing.coefficient,
                        "box_type_name": existing.box_type_name,
                        "updated": True
                    })

    session.close()
    return all_new_coeffs

def parse_datetime_z(dt_str: str) -> datetime.datetime | None:
    """
    Парсит строку вида '2025-03-12T00:00:00Z' в datetime (UTC).
    """
    if not dt_str:
        return None
    try:
        # Python 3.11: datetime.fromisoformat() может игнорировать 'Z'.
        # Для совместимости используем strptime:
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"  # меняем Z на +00:00
        dt = datetime.datetime.fromisoformat(dt_str)
        return dt
    except ValueError:
        return None

def parse_float_wb(s: str | None) -> float | None:
    """
    Преобразует WB-строку вида '18,53' в float 18.53
    Если None или пустая строка - возвращает None
    """
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def parse_float_or_none(s: str | None) -> float | None:
    """
    Аналогично parse_float_wb, если данные в нормальном формате (например, '195')
    """
    return parse_float_wb(s)
