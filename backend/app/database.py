from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/stock_analysis")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_vector_extension():
    """
    pgvector 확장을 활성화합니다.
    데이터베이스 초기화 시 한 번만 실행하면 됩니다.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            print("✅ pgvector 확장이 활성화되었습니다.")
    except Exception as e:
        print(f"⚠️  pgvector 확장 활성화 중 오류 발생: {e}")
        print("   (이미 활성화되어 있거나 권한 문제일 수 있습니다.)")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
