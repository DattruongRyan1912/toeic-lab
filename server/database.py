from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from server.config import DATABASE_URL

# SQLite check for thread connect args
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import server.models  # Ensure all models are registered
    Base.metadata.create_all(bind=engine)
