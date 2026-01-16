from sqlalchemy import create_engine, text, inspect
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

def initialize_schema():
    """
    데이터베이스 스키마를 초기화하고 코드의 모델과 동기화합니다.
    서버 시작 시 호출되어 테이블 생성 및 스키마 업데이트를 수행합니다.
    """
    print("=" * 60)
    print("🔧 데이터베이스 스키마 초기화 시작...")
    print("=" * 60)
    
    try:
        # 1. pgvector 확장 활성화
        init_vector_extension()
        
        # 2. 기본 테이블 생성 (없는 경우에만 생성)
        Base.metadata.create_all(bind=engine)
        print("✅ 기본 테이블 생성 완료")
        
        # 3. news_articles 테이블의 특수 컬럼 추가 (embedding, metadata)
        init_news_articles_schema()
        
        # 4. 스키마 동기화 (컬럼 추가/수정)
        sync_schema()
        
        print("=" * 60)
        print("✅ 데이터베이스 스키마 초기화 완료")
        print("=" * 60)
        
    except Exception as e:
        print("=" * 60)
        print(f"❌ 스키마 초기화 중 오류 발생: {e}")
        import traceback
        print(traceback.format_exc())
        print("=" * 60)
        raise


def sync_schema():
    """
    현재 데이터베이스 스키마를 코드의 모델과 동기화합니다.
    누락된 컬럼을 추가하고 인덱스를 생성합니다.
    """
    inspector = inspect(engine)
    
    # models 모듈 import (모든 모델을 로드하기 위해)
    import sys
    backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    try:
        from models import models
    except ImportError:
        print("⚠️  models 모듈을 import할 수 없습니다. 스키마 동기화를 건너뜁니다.")
        return
    
    with engine.connect() as conn:
        # 각 테이블의 스키마를 확인하고 필요한 컬럼 추가
        for table_name, table in Base.metadata.tables.items():
            if inspector.has_table(table_name):
                existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
                model_columns = {col.name for col in table.columns}
                
                # 누락된 컬럼 추가
                missing_columns = model_columns - existing_columns
                if missing_columns:
                    print(f"📝 {table_name} 테이블에 누락된 컬럼 발견: {missing_columns}")
                    for col_name in missing_columns:
                        col = table.columns[col_name]
                        add_column_sql = _generate_add_column_sql(table_name, col)
                        try:
                            conn.execute(text(add_column_sql))
                            conn.commit()
                            print(f"  ✅ 컬럼 추가: {table_name}.{col_name}")
                        except Exception as e:
                            print(f"  ⚠️  컬럼 추가 실패 ({col_name}): {e}")
                            conn.rollback()
                
                # 인덱스 확인 및 생성
                existing_indexes = {idx['name'] for idx in inspector.get_indexes(table_name)}
                for index in table.indexes:
                    if index.name and index.name not in existing_indexes:
                        try:
                            index_sql = _generate_create_index_sql(table_name, index)
                            conn.execute(text(index_sql))
                            conn.commit()
                            print(f"  ✅ 인덱스 생성: {table_name}.{index.name}")
                        except Exception as e:
                            print(f"  ⚠️  인덱스 생성 실패 ({index.name}): {e}")
                            conn.rollback()


def _generate_add_column_sql(table_name: str, column) -> str:
    """컬럼 추가 SQL 생성"""
    col_type = str(column.type)
    
    # PostgreSQL 타입 변환
    if 'VARCHAR' in col_type or 'String' in col_type:
        length = getattr(column.type, 'length', None)
        if length:
            col_type = f"VARCHAR({length})"
        else:
            col_type = "VARCHAR"
    elif 'TEXT' in col_type or 'Text' in col_type:
        col_type = "TEXT"
    elif 'INTEGER' in col_type or 'Integer' in col_type:
        col_type = "INTEGER"
    elif 'TIMESTAMP' in col_type:
        col_type = "TIMESTAMP"
    elif 'DATE' in col_type:
        col_type = "DATE"
    elif 'DECIMAL' in col_type:
        precision = getattr(column.type, 'precision', None)
        scale = getattr(column.type, 'scale', None)
        if precision and scale:
            col_type = f"DECIMAL({precision}, {scale})"
        else:
            col_type = "DECIMAL"
    elif 'JSONB' in col_type:
        col_type = "JSONB"
    
    nullable = "NULL" if column.nullable else "NOT NULL"
    default = ""
    
    if column.server_default:
        default = f" DEFAULT {column.server_default.arg}"
    
    return f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} {nullable}{default}"


def _generate_create_index_sql(table_name: str, index) -> str:
    """인덱스 생성 SQL 생성"""
    columns = ", ".join([col.name for col in index.columns])
    unique = "UNIQUE " if index.unique else ""
    return f"CREATE {unique}INDEX IF NOT EXISTS {index.name} ON {table_name} ({columns})"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
