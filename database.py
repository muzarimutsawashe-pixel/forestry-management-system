import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()


# ============================================================
# DATABASE CONNECTION
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Create a .env file in the backend folder "
        "with DATABASE_URL=postgresql+psycopg2://..."
    )


# ============================================================
# DATABASE ENGINE
# ============================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    connect_args={
        "sslmode": "require",
        "connect_timeout": 10,
    },
)


# ============================================================
# SESSION
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ============================================================
# BASE
# ============================================================

Base = declarative_base()


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()