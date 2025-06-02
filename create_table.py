# create_tables.py
from db.database import engine
from db.models import Base

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Таблицы созданы")
