"""
분석 API 라우터
뉴스 수집 및 AI 분석을 트리거하는 API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ValidationError, field_validator, ConfigDict
from datetime import date, datetime
from typing import Optional
from app.database import get_db
from app.news import collect_news
from app.analysis import analyze_and_save
import sys
import os

# models 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from models.models import NewsArticle, Report

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """분석 요청 모델"""
    model_config = ConfigDict(
        json_schema_extra=lambda schema: schema.update({
            "example": {
                "date": date.today().strftime("%Y-%m-%d"),
                "query": "주식",
                "size": 10,
                "force": False
            }
        })
    )
    
    date: Optional[str] = Field(
        None, 
        description=f"YYYY-MM-DD 형식의 날짜 (예: {date.today().strftime('%Y-%m-%d')})"
    )
    query: str = Field("주식", description="뉴스 검색 쿼리", examples=["주식", "증시", "반도체"])
    size: int = Field(
        10, 
        ge=1, 
        le=10, 
        description="가져올 뉴스 개수 (1-10, 무료 티어 제한)", 
        examples=[10]  # Swagger 예시 값
    )
    force: bool = Field(False, description="이미 분석된 날짜도 재분석할지 여부", examples=[False, True])
    
    @field_validator('date', mode='before')
    @classmethod
    def validate_date(cls, v):
        """날짜 형식 검증"""
        # None이거나 빈 값인 경우 None 반환
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError(f"날짜는 문자열이어야 합니다. (받은 타입: {type(v).__name__}, 값: {repr(v)})")
        
        # 빈 문자열이나 공백만 있는 경우 None 반환
        v = v.strip()
        if not v:
            return None
        
        # 날짜 형식 검증
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return v
        except ValueError:
            raise ValueError(f"날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요. (받은 값: '{v}')")


class AnalyzeResponse(BaseModel):
    """분석 응답 모델"""
    report_id: int
    status: str
    message: str
    news_count: int


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_news(
    request: AnalyzeRequest,
    db: Session = Depends(get_db)
):
    """
    뉴스를 수집하고 AI로 분석하여 보고서를 생성합니다.
    """
    try:
        # 요청 로깅
        print(f"분석 요청 받음: query={request.query}, size={request.size}, date={request.date}, force={request.force}")
        
        # 날짜 파싱
        analysis_date = date.today()
        if request.date and request.date.strip():  # None이 아니고 빈 문자열도 아님
            date_str = request.date.strip()
            try:
                analysis_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                print(f"날짜 파싱 성공: {analysis_date}")
            except ValueError as e:
                print(f"날짜 파싱 실패: '{date_str}' - {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요. (받은 값: '{date_str}')"
                )
        else:
            print(f"날짜 미지정, 오늘 날짜 사용: {analysis_date}")
        
        # 이미 분석된 날짜인지 확인
        if not request.force:
            existing_report = db.query(Report).filter(
                Report.analysis_date == analysis_date
            ).first()
            
            if existing_report:
                return AnalyzeResponse(
                    report_id=existing_report.id,
                    status="already_exists",
                    message=f"{analysis_date}에 대한 보고서가 이미 존재합니다. force=true로 재분석할 수 있습니다.",
                    news_count=0
                )
        
        # 뉴스 수집
        news_articles = collect_news(db, query=request.query, size=request.size)
        
        if not news_articles:
            raise HTTPException(
                status_code=404,
                detail="수집된 뉴스가 없습니다. 검색 쿼리를 조정해주세요."
            )
        
        # AI 분석 및 저장
        report = analyze_and_save(db, news_articles, analysis_date)
        
        return AnalyzeResponse(
            report_id=report.id,
            status="completed",
            message="분석이 완료되었습니다.",
            news_count=len(news_articles)
        )
    
    except ValueError as e:
        print(f"ValueError 발생: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except TypeError as e:
        print(f"TypeError 발생: {e}")
        raise HTTPException(status_code=400, detail=f"요청 형식 오류: {str(e)}")
    except HTTPException:
        raise  # HTTPException은 그대로 전달
    except Exception as e:
        import traceback
        error_detail = str(e)
        error_traceback = traceback.format_exc()
        print(f"분석 중 오류 발생: {error_detail}")
        print(f"Traceback: {error_traceback}")
        raise HTTPException(
            status_code=500, 
            detail=f"분석 중 오류가 발생했습니다: {error_detail}"
        )
