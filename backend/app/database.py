
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Default path is unchanged; an environment override enables isolated reproducibility runs.
_DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "sellerpulse.db"
DATABASE_PATH = Path(os.environ.get("SELLERPULSE_DATABASE_PATH", str(_DEFAULT_DATABASE_PATH))).resolve()
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
