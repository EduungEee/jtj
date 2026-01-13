from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.database import engine, Base
from app.routers import health, analyze, reports
import sys
import os

# models 모듈 import (테이블 생성용)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from models import models

# pgvector 확장 활성화
from app.database import init_vector_extension
init_vector_extension()

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(reports.router, prefix="/api", tags=["reports"])

@app.get("/")
async def root():
    return {"message": "Stock Analysis API"}
