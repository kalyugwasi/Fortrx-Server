from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

DATABASE_URL = settings.DATABASE_URL

if DATABASE_URL.startswith("postgresql+asyncpg"):
    sync_database_url = DATABASE_URL.replace("+asyncpg", "+psycopg2")
else:
    sync_database_url = DATABASE_URL

engine = create_engine(sync_database_url, echo=settings.SQL_ECHO, future=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def ensure_key_bundle_schema():
    inspector = inspect(engine)
    if not inspector.has_table("key_bundles"):
        return

    columns = {column["name"] for column in inspector.get_columns("key_bundles")}
    if "signing_public" in columns:
        return

    dialect = engine.dialect.name
    with engine.begin() as connection:
        if dialect == "sqlite":
            connection.execute(text("ALTER TABLE key_bundles ADD COLUMN signing_public TEXT"))
        else:
            connection.execute(text("ALTER TABLE key_bundles ADD COLUMN IF NOT EXISTS signing_public TEXT"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
