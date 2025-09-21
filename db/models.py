from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, LargeBinary, Text, BigInteger, ForeignKey, LargeBinary, UniqueConstraint, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    subscription_until = Column(DateTime, nullable=True)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=True)
    token = relationship("Token", backref="users")
    store_link = Column(Text, nullable=True)  # Новый столбец
    notify_orders = Column(Boolean, default=True)
    notify_sales = Column(Boolean, default=True)
    notify_daily_report = Column(Boolean, default=True)
    notify_incomes = Column(Boolean, default=True)
    notify_cancel = Column(Boolean, default=True)

class UserWarehouse(Base):
    __tablename__ = 'user_warehouses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    warehouse_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Чтобы один пользователь не мог добавить один и тот же склад несколько раз
    __table_args__ = (
        UniqueConstraint('user_id', 'warehouse_id', name='uq_user_warehouse'),
    )

    # relationship для удобства, если нужно
    user = relationship("User", backref="tracked_warehouses")

class UserBoxType(Base):
    __tablename__ = 'user_box_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    box_type_name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'box_type_name', name='uq_user_box_type'),
    )

    user = relationship("User", backref="tracked_box_types")

class Token(Base):
    __tablename__ = 'tokens'

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_value = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    subscription_until = Column(DateTime, nullable=True)  # До какого момента действует подписка
    role = Column(String(50), default="free")            # free, premium, enterprise и т.д.
    is_active = Column(Boolean, default=True, index=True)   # ← новый столбец

    # --- автоплатежи ---
    autopay_enabled = Column(Boolean, default=False, index=True)          # вкл/выкл у пользователя
    yk_payment_method_id = Column(String(128), nullable=True, index=True) # id сохранённого способа оплаты
    autopay_merchant_customer_id = Column(String(64), nullable=True)      # твой ID клиента (telegram_id, user.id и т.п.)
    autopay_last_charge_at = Column(DateTime, nullable=True)
    autopay_next_charge_at = Column(DateTime, nullable=True)
    autopay_fail_count = Column(Integer, default=0)

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=True)

    tariff = Column(String(32), nullable=False)            # 'base' | 'advanced'
    amount = Column(Numeric(10, 2), nullable=False)        # 349.00
    currency = Column(String(3), default="RUB", nullable=False)

    yk_payment_id = Column(String(128), index=True, nullable=False)  # id платежа в ЮKassa
    status = Column(String(32), default="pending", nullable=False)   # pending | succeeded | canceled
    description = Column(Text, nullable=True)                        # для логов/диагностики

    # --- автоплатежи/реккаринг ---
    is_recurring = Column(Boolean, default=False, nullable=False)    # True для автосписаний
    yk_payment_method_id = Column(String(128), nullable=True)        # каким методом списали
    parent_payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)

    user = relationship("User", backref="payments")
    token = relationship("Token", backref="payments")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    srid = Column(String, unique=True, index=True)  # уникальный идентификатор
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
    last_change_date = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    date = Column(DateTime, nullable=True)
    warehouse_name = Column(String)  # название склада
    region_name = Column(String)  # регион
    subject = Column(String)  # название товара
    supplier_article = Column(String)  # артикул поставщика
    full_supplier_article = Column(String)  # полное название товара
    techSize = Column(String)  # размер
    nm_id = Column(Integer)  # ID товара
    brand = Column(String)  # бренд
    price_with_disc = Column(Float)  # цена с учетом скидки
    total_price = Column(Float)  # общая цена
    spp = Column(Integer)  # скидка в процентах
    is_cancel = Column(Boolean, default=False)  # отменен ли заказ (отказ)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
    nm_id = Column(Integer, unique=True, index=True, nullable=False)  # Артикул WB
    subject_name = Column(String, nullable=True)  # название товара
    brand_name = Column(String, nullable=True)  # бренд товара
    supplier_article = Column(String, nullable=True)  # артикул поставщика
    techSize = Column(String)  # размер
    image_url = Column(String, nullable=True)  # URL изображения
    rating = Column(Float, nullable=True)  # рейтинг
    reviews = Column(Integer, nullable=True)  # количество отзывов
    last_update = Column(DateTime, default=datetime.datetime.utcnow)  # дата последнего обновления
    resize_img = Column(LargeBinary, nullable=True)  # уменьшенное изображение

class ReportDetails(Base):
    __tablename__ = "report_details"

    id = Column(Integer, primary_key=True, index=True)
    create_dt = Column(String, nullable=False)  # дата создания
    nm_id = Column(Integer, nullable=False)  # артикул товара
    office_name = Column(String, nullable=False)  # пункт выдачи заказа
    order_dt = Column(String, nullable=False)  # дата заказа
    commission_percent = Column(Float, default=0.0)  # процент комиссии
    report_type = Column(Integer, server_default="0", nullable=True)  # тип отчета


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
    sale_id = Column(String, unique=True, index=True, nullable=False)  # Уникальный идентификатор выкупа
    last_change_date = Column(DateTime, default=datetime.datetime.utcnow)
    date = Column(DateTime, nullable=True)  # дата выкупа
    warehouse_name = Column(String, nullable=True)
    region_name = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    techSize = Column(String)
    nm_id = Column(Integer, nullable=True)
    brand = Column(String, nullable=True)
    price_with_disc = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)
    spp = Column(Float, default=0.0)


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    last_change_date = Column(DateTime, default=datetime.datetime.utcnow) # Дата последнего изменения
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
    nm_id = Column(Integer, nullable=False, index=True)  # Артикул WB
    warehouseName = Column(String, nullable=True) # Название склада
    quantity = Column(Integer, nullable=True)  # Доступное количество
    quantity_full = Column(Integer, nullable=True)  # Полное количество
    subject = Column(String(50), nullable=True)  # Предмет
    inWayToClient = Column(Integer, nullable=True)  # Количество товара в пути к клиенту

class Income(Base):
    __tablename__ = "incomes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Токен, к которому относится данная поставка (связь через Token.id)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)

    income_id = Column(Integer, index=True)         # incomeId
    number = Column(String(40), nullable=True)       # number
    date = Column(DateTime, nullable=True)           # date
    last_change_date = Column(DateTime, nullable=True)   # lastChangeDate
    supplier_article = Column(String(75), nullable=True) # supplierArticle
    tech_size = Column(String(30), nullable=True)    # techSize
    barcode = Column(String(30), nullable=True)       # barcode
    quantity = Column(Integer, default=0)            # quantity
    total_price = Column(Float, default=0.0)         # totalPrice
    date_close = Column(DateTime, nullable=True)     # dateClose
    warehouse_name = Column(String(50), nullable=True)  # warehouseName
    nm_id = Column(Integer, nullable=True)           # nmId
    status = Column(String(50), nullable=True)       # status


class AcceptanceCoefficient(Base):
    __tablename__ = "acceptance_coefficients"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Ссылка на токен (если нужно привязать к конкретному продавцу)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)

    date = Column(DateTime, nullable=True)  # 2025-03-12T00:00:00Z -> DateTime
    coefficient = Column(Float, default=0.0)     # -1, 0, 1...
    warehouse_id = Column(Integer, nullable=True)
    warehouse_name = Column(String(100), nullable=True)
    allow_unload = Column(Boolean, default=True)
    box_type_name = Column(String(50), nullable=True)
    box_type_id = Column(Integer, nullable=True)
    storage_coef = Column(Float, nullable=True)
    delivery_coef = Column(Float, nullable=True)
    delivery_base_liter = Column(Float, nullable=True)
    delivery_additional_liter = Column(Float, nullable=True)
    storage_base_liter = Column(Float, nullable=True)
    storage_additional_liter = Column(Float, nullable=True)
    is_sorting_center = Column(Boolean, default=False)

    # Когда мы это записали в нашу БД
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class PopularRequest(Base):
    __tablename__ = "popular_request"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(Text, nullable=False)
    request_count = Column(Integer, nullable=False)
    load_date = Column(DateTime, default=datetime.datetime.utcnow)

class DestCity(Base):
    __tablename__ = "dest_city"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(255), nullable=False) # Название города
    dest = Column(BigInteger, nullable=False) # ID города 

class ProductPositions(Base):
    __tablename__ = "product_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
    nm_id = Column(Integer, nullable=False)
    city_id = Column(Integer, nullable=False)
    query_text = Column(Text, nullable=False)
    request_count = Column(Integer, nullable=True)
    page = Column(Integer, nullable=True)
    position = Column(Integer, nullable=True)
    check_dt = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    city_id = Column(Integer, ForeignKey("dest_city.id"), nullable=False)

class ProductSearchRequest(Base):
    __tablename__ = "product_search_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nm_id = Column(Integer, index=True, nullable=False)
    search_text = Column(String, nullable=False)
    current_freq = Column(Integer, default=0)
    last_update = Column(DateTime, server_default=func.now(), nullable=False)


class TrackedPosition(Base):
    __tablename__ = "tracked_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("popular_request.id"), nullable=False)
    product_id = Column(Integer, nullable=False)  # 'id' из JSON
    page = Column(Integer, nullable=False)
    position = Column(Integer, nullable=False)
    check_dt = Column(DateTime, default=datetime.datetime.utcnow)

class Media(Base):
    __tablename__ = 'media'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    resize_img = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LogisticTariff(Base):
    __tablename__ = "logistic_tariffs"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_id  = Column(String(50), nullable=False)
    box_type_id   = Column(Integer, nullable=False)
    box_type_name = Column(String(50), nullable=True)
    tariff_rub    = Column(Float, nullable=False)          # стоимость в ₽
    updated_at    = Column(DateTime, default=datetime.datetime.utcnow,
                                         onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('warehouse_id', 'box_type_id',
                         name='uq_wh_box_type'),           # 1 запись – 1 склад+тара
    )