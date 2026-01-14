from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.database import engine, Base
from app.routers import health, analyze, reports, news
from app.scheduler import start_scheduler, stop_scheduler
import sys
import os

# models 모듈 import (테이블 생성용)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models import models

# pgvector 확장 활성화
from app.database import init_vector_extension, init_news_articles_schema
init_vector_extension()

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# news_articles 테이블에 embedding, metadata 컬럼 추가
init_news_articles_schema()

app = FastAPI(title="Stock Analysis API", version="1.0.0")

# 요청 검증 오류 핸들러
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 오류를 상세하게 로깅"""
    errors = exc.errors()
    error_details = []
    for error in errors:
        error_details.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    print(f"요청 검증 실패: {error_details}")
    return JSONResponse(
        status_code=400,
        content={
            "detail": "요청 형식이 올바르지 않습니다.",
            "errors": error_details
        }
    )

# CORS 설정
# 환경 변수에서 허용할 origin 목록 가져오기
allowed_origins = ["http://localhost:3000"]  # 개발 환경

# 프로덕션 환경 변수에서 추가 origin 가져오기
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

# Vercel 도메인 목록 (쉼표로 구분)
vercel_domains = os.getenv("VERCEL_DOMAINS", "")
if vercel_domains:
    # 쉼표로 구분된 도메인 목록을 파싱
    domains = [domain.strip() for domain in vercel_domains.split(",") if domain.strip()]
    allowed_origins.extend(domains)

# 환경 변수로 모든 origin 허용 옵션 (개발용, 프로덕션에서는 사용하지 않음)
allow_all_origins = os.getenv("CORS_ALLOW_ALL", "false").lower() == "true"
if allow_all_origins:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(news.router, prefix="/api", tags=["news"])

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 스케줄러 초기화"""
    start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 스케줄러 중지"""
    stop_scheduler()


@app.get("/")
async def root():
    return {"message": "Stock Analysis API"}
