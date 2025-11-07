from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

Base = declarative_base()

def build_engine():
    if settings.DATABASE_URL:
        return create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            future=True,
        )

    connection_url = URL.create(
        "postgresql+psycopg2",
        username=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
    )

    return create_engine(connection_url, pool_pre_ping=True, future=True)

engine = build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
