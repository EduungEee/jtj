"""
뉴스 수집 및 조회 API 라우터
뉴스 수집 및 조회 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import List, Optional
from app.database import get_db
from app.news import collect_news, fetch_news_from_api
import sys
import os

# models 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from models.models import NewsArticle

router = APIRouter()


# 요청 모델 정의
class NewsCollectionRequest(BaseModel):
    """뉴스 수집 요청 모델
    
    newsdata.io API를 사용하여 한국 관련 뉴스를 수집합니다.
    자동으로 다음 파라미터가 적용됩니다:
    - country=kr (한국)
    - language=ko (한국어)
    - timezone=asia/seoul (한국 시간대)
    - image=0 (이미지 제외)
    - video=0 (비디오 제외)
    - removeduplicate=1 (중복 제거)
    """
    query: str = Field(
        default="주식 OR 증시 OR 코스피 OR 코스닥 OR 반도체 OR 경제 OR 금리 OR 부동산 OR 주가 OR 투자",
        description="검색 쿼리 (OR 연산자로 여러 키워드 연결 가능, 예: '주식 OR 증시 OR 경제')"
    )
    size: int = Field(
        default=10, 
        ge=1, 
        le=10, 
        description="가져올 뉴스 개수 (1-10, 무료 티어 제한)",
        examples=[10]  # Swagger 예시 값
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "주식 OR 증시 OR 코스피 OR 코스닥 OR 반도체 OR 경제 OR 금리 OR 부동산 OR 주가 OR 투자",
                "size": 10
            }
        }


# 응답 모델 정의
class NewsArticleResponse(BaseModel):
    """뉴스 기사 응답 모델"""
    id: int
    title: str
    content: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class NewsCollectionResponse(BaseModel):
    """뉴스 수집 응답 모델"""
    message: str
    collected_count: int
    articles: List[NewsArticleResponse]


@router.post("/get_news", response_model=NewsCollectionResponse)
async def collect_news_endpoint(
    request: NewsCollectionRequest,
    db: Session = Depends(get_db)
):
    """
    뉴스를 수집하고 데이터베이스에 저장합니다.
    
    newsdata.io API를 사용하여 한국 관련 뉴스를 수집합니다.
    
    **자동 적용되는 파라미터:**
    - country=kr (한국)
    - language=ko (한국어)
    - timezone=asia/seoul (한국 시간대)
    - image=0 (이미지 제외)
    - video=0 (비디오 제외)
    - removeduplicate=1 (중복 제거)
    
    **요청 파라미터:**
    - **query**: 검색 쿼리 (OR 연산자로 여러 키워드 연결 가능)
      - 기본값: "주식 OR 증시 OR 코스피 OR 코스닥 OR 반도체 OR 경제 OR 금리 OR 부동산 OR 주가 OR 투자"
      - 예시: "주식 OR 증시", "경제 OR 금리", "반도체 OR 반도체주"
    - **size**: 가져올 뉴스 개수 (1-10, 기본값: 10, 무료 티어 제한)
    
    **예시 요청:**
    ```json
    {
      "query": "주식 OR 증시 OR 코스피 OR 코스닥 OR 반도체 OR 경제 OR 금리 OR 부동산 OR 주가 OR 투자",
      "size": 10
    }
    ```
    """
    try:
        # size 범위 검증 (무료 티어 제한: 1-10)
        if request.size < 1 or request.size > 10:
            raise HTTPException(
                status_code=400,
                detail="size는 1-10 사이의 값이어야 합니다. (무료 티어 제한)"
            )
        
        # 뉴스 수집 및 저장
        saved_articles = collect_news(
            db=db,
            query=request.query,
            size=request.size
        )
        
        # 응답 데이터 구성
        articles_response = [
            NewsArticleResponse(
                id=article.id,
                title=article.title,
                content=article.content,
                source=article.source,
                url=article.url,
                published_at=article.published_at,
                collected_at=article.collected_at
            )
            for article in saved_articles
        ]
        
        return NewsCollectionResponse(
            message=f"뉴스 수집 완료: {len(saved_articles)}개 저장됨",
            collected_count=len(saved_articles),
            articles=articles_response
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"뉴스 수집 중 오류 발생: {str(e)}"
        )


@router.get("/news", response_model=List[NewsArticleResponse])
async def get_news(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100, description="조회할 뉴스 개수"),
    offset: int = Query(default=0, ge=0, description="건너뛸 뉴스 개수"),
    start_date: Optional[date] = Query(default=None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(default=None, description="종료 날짜 (YYYY-MM-DD)"),
    keyword: Optional[str] = Query(default=None, description="제목 또는 내용 검색 키워드")
):
    """
    저장된 뉴스 기사 목록을 조회합니다.
    
    - **limit**: 조회할 뉴스 개수 (1-100, 기본값: 50)
    - **offset**: 건너뛸 뉴스 개수 (기본값: 0)
    - **start_date**: 시작 날짜 (YYYY-MM-DD 형식)
    - **end_date**: 종료 날짜 (YYYY-MM-DD 형식)
    - **keyword**: 제목 또는 내용에서 검색할 키워드
    """
    try:
        # 기본 쿼리
        query = db.query(NewsArticle)
        
        # 날짜 필터링
        if start_date:
            query = query.filter(NewsArticle.published_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(NewsArticle.published_at <= datetime.combine(end_date, datetime.max.time()))
        
        # 키워드 필터링
        if keyword:
            query = query.filter(
                (NewsArticle.title.contains(keyword)) |
                (NewsArticle.content.contains(keyword))
            )
        
        # 정렬 및 페이징
        articles = query.order_by(
            NewsArticle.published_at.desc()
        ).offset(offset).limit(limit).all()
        
        # 응답 데이터 구성
        return [
            NewsArticleResponse(
                id=article.id,
                title=article.title,
                content=article.content,
                source=article.source,
                url=article.url,
                published_at=article.published_at,
                collected_at=article.collected_at
            )
            for article in articles
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"뉴스 조회 중 오류 발생: {str(e)}"
        )

