import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
engine = create_engine(os.getenv("DATABASE_URL", "postgresql+psycopg2://quant:quant@localhost:5432/quantniti"), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
