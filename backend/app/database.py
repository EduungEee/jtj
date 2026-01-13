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


def init_news_articles_schema():
    """
    news_articles 테이블에 embedding과 metadata 컬럼을 추가합니다.
    이미 존재하는 경우 무시됩니다.
    """
    try:
        with engine.connect() as conn:
            # embedding 컬럼 추가 (vector(1536) 타입)
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'news_articles' AND column_name = 'embedding'
                    ) THEN
                        ALTER TABLE news_articles ADD COLUMN embedding vector(1536);
                        CREATE INDEX IF NOT EXISTS news_articles_embedding_idx 
                        ON news_articles USING ivfflat (embedding vector_cosine_ops);
                    END IF;
                END $$;
            """))
            
            # metadata 컬럼 추가 (JSONB 타입)
            conn.execute(text("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'news_articles' AND column_name = 'metadata'
                    ) THEN
                        ALTER TABLE news_articles ADD COLUMN metadata JSONB;
                        CREATE INDEX IF NOT EXISTS news_articles_metadata_idx 
                        ON news_articles USING gin (metadata);
                    END IF;
                END $$;
            """))
            
            conn.commit()
            print("✅ news_articles 테이블 스키마 업데이트 완료 (embedding, metadata 컬럼)")
    except Exception as e:
        print(f"⚠️  news_articles 스키마 업데이트 중 오류 발생: {e}")
        print("   (이미 컬럼이 존재하거나 권한 문제일 수 있습니다.)")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
