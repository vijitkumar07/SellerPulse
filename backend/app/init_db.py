
from .database import Base, engine
from . import models  # noqa: F401


def init_db():
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized: {engine.url.database}")
    print("Tables:")
    for table_name in Base.metadata.tables:
        print(f" - {table_name}")


if __name__ == "__main__":
    init_db()
