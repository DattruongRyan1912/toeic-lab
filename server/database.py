import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from server.config import DATABASE_URL

logger = logging.getLogger(__name__)

# SQLite needs check_same_thread=False because FastAPI serves sync routes from a threadpool.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_missing_columns() -> list:
    """Additive, idempotent migration.

    ``create_all`` creates missing tables but never alters existing ones, so databases
    created by older versions would miss newly added (nullable) columns. Only nullable
    columns are added; nothing is dropped or rewritten.
    """
    inspector = inspect(engine)
    added = []
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {column["name"] for column in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                if column.primary_key or not column.nullable:
                    logger.warning("Skip migrating non-nullable column %s.%s", table.name, column.name)
                    continue
                column_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column_type}'))
                added.append(f"{table.name}.{column.name}")
    return added


def init_db() -> list:
    import server.models  # noqa: F401  (registers every model on Base.metadata)

    Base.metadata.create_all(bind=engine)
    added = _add_missing_columns()
    if added:
        logger.info("Database migrated, added columns: %s", ", ".join(added))
    return added
