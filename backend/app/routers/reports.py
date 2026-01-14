"""
보고서 조회 API 라우터
보고서 목록 및 상세 조회 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional
from app.database import get_db
import sys
import os

# models 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from models.models import Report, ReportIndustry, ReportStock, NewsArticle

router = APIRouter()


# 응답 모델 정의
class NewsArticleResponse(BaseModel):
    """뉴스 기사 응답 모델"""
    id: int
    title: str
    content: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class StockResponse(BaseModel):
    """주식 응답 모델"""
    id: int
    stock_code: Optional[str] = None
    stock_name: Optional[str] = None
    expected_trend: Optional[str] = None
    confidence_score: Optional[float] = None
    reasoning: Optional[str] = None
    
    class Config:
        from_attributes = True


class IndustryResponse(BaseModel):
    """산업 응답 모델"""
    id: int
    industry_name: str
    impact_level: Optional[str] = None
    impact_description: Optional[str] = None
    trend_direction: Optional[str] = None
    stocks: List[StockResponse] = []
    
    class Config:
        from_attributes = True


class ReportDetailResponse(BaseModel):
    """보고서 상세 응답 모델"""
    id: int
    title: str
    summary: Optional[str] = None
    analysis_date: date
    created_at: datetime
    news_articles: List[NewsArticleResponse] = []
    industries: List[IndustryResponse] = []
    
    class Config:
        from_attributes = True


class ReportListItemResponse(BaseModel):
    """보고서 목록 항목 응답 모델"""
    id: int
    title: str
    summary: Optional[str] = None
    analysis_date: date
    created_at: datetime
    news_count: int = 0
    industry_count: int = 0
    
    class Config:
        from_attributes = True


@router.get("/report/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    """
    보고서 상세 정보를 조회합니다.
    """
    # 보고서 조회 (관계 데이터를 한 번에 로드하여 N+1 문제 방지)
    report = db.query(Report).options(
        joinedload(Report.news_articles),
        joinedload(Report.industries).joinedload(ReportIndustry.stocks)
    ).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"보고서를 찾을 수 없습니다. (ID: {report_id})"
        )
    
    return report


@router.get("/reports", response_model=List[ReportListItemResponse])
async def get_all_reports(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    전체 보고서 목록을 조회합니다 (최신순).
    """
    # 전체 보고서 조회 (관계 데이터도 함께 로드)
    reports = db.query(Report).options(
        joinedload(Report.news_articles),
        joinedload(Report.industries)
    ).order_by(Report.created_at.desc()).limit(limit).all()
    
    # 각 보고서의 뉴스 개수와 산업 개수 계산
    result = []
    for report in reports:
        news_count = len(report.news_articles) if report.news_articles else 0
        industry_count = len(report.industries) if report.industries else 0
        
        result.append(ReportListItemResponse(
            id=report.id,
            title=report.title,
            summary=report.summary,
            analysis_date=report.analysis_date,
            created_at=report.created_at,
            news_count=news_count,
            industry_count=industry_count
        ))
    
    return result


@router.get("/reports/today", response_model=List[ReportListItemResponse])
async def get_today_reports(
    db: Session = Depends(get_db)
):
    """
    오늘 날짜로 분석된 보고서 목록을 조회합니다.
    """
    today = date.today()
    
    # 오늘 날짜의 보고서 조회 (관계 데이터도 함께 로드)
    reports = db.query(Report).options(
        joinedload(Report.news_articles),
        joinedload(Report.industries)
    ).filter(
        Report.analysis_date == today
    ).order_by(Report.created_at.desc()).all()
    
    # 각 보고서의 뉴스 개수와 산업 개수 계산
    result = []
    for report in reports:
        news_count = len(report.news_articles) if report.news_articles else 0
        industry_count = len(report.industries) if report.industries else 0
        
        result.append(ReportListItemResponse(
            id=report.id,
            title=report.title,
            summary=report.summary,
            analysis_date=report.analysis_date,
            created_at=report.created_at,
            news_count=news_count,
            industry_count=industry_count
        ))
    
    return result
