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
from app.analysis import analyze_and_save, analyze_news_from_vector_db
from datetime import datetime, timedelta
import pytz
import httpx
import sys
import os

# models 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from models.models import NewsArticle, Report

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """분석 요청 모델 - 벡터 DB에서 뉴스를 조회하여 분석"""
    model_config = ConfigDict(
        json_schema_extra=lambda schema: schema.update({
            "example": {
                "date": date.today().strftime("%Y-%m-%d"),
                "force": False
            }
        })
    )
    
    date: Optional[str] = Field(
        None, 
        description=f"YYYY-MM-DD 형식의 분석 날짜 (예: {date.today().strftime('%Y-%m-%d')}). 기본값: 오늘"
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
    벡터 DB에서 뉴스를 조회하고 AI로 분석하여 보고서를 생성합니다.
    벡터 DB에서 현재 시간~전날 아침 6시 사이의 뉴스 기사를 조회합니다.
    """
    try:
        # 요청 로깅
        print(f"분석 요청 받음: date={request.date}, force={request.force}")
        
        # 한국 시간대 설정 (날짜 계산에 사용)
        seoul_tz = pytz.timezone('Asia/Seoul')
        now_kst = datetime.now(seoul_tz)
        
        # 날짜 파싱
        # 기본값은 한국 시간 기준 오늘 날짜
        analysis_date = now_kst.date()
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
            print(f"날짜 미지정, 한국 시간 기준 오늘 날짜 사용: {analysis_date}")
        
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
        
        # 한국 시간대 설정 (뉴스 조회 시간 범위 계산에 사용)
        # seoul_tz와 now는 위에서 이미 설정됨
        now = now_kst
        
        # 전날 06:00:00 계산
        yesterday_6am = (now - timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
        
        # 현재 시간을 종료 시간으로 설정
        end_datetime = now
        
        print(f"📅 벡터 DB에서 뉴스 조회: {yesterday_6am.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 벡터 DB에서 뉴스 조회 및 분석
        report = analyze_news_from_vector_db(
            db=db,
            start_datetime=yesterday_6am,
            end_datetime=end_datetime,
            analysis_date=analysis_date
        )
        
        # 뉴스 개수 계산
        news_count = len(report.news_articles) if report.news_articles else 0
        
        return AnalyzeResponse(
            report_id=report.id,
            status="completed",
            message="분석이 완료되었습니다.",
            news_count=news_count
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
