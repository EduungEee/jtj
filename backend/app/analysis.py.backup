"""
AI 분석 모듈
OpenAI API를 사용하여 뉴스를 분석하고 산업/주식 예측을 수행합니다.
"""
import os
import json
from typing import List, Dict, Optional
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from datetime import date, datetime, timedelta
import pytz
import sys
import os as os_module

# models 경로 추가
backend_path = os_module.path.dirname(os_module.path.dirname(os_module.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from models.models import NewsArticle, Report, ReportIndustry, ReportStock

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_openai_client():
    """OpenAI 클라이언트를 지연 초기화합니다."""
    if not OPENAI_API_KEY:
        return None
    return OpenAI(api_key=OPENAI_API_KEY)


def create_query_embedding(query_text: str) -> Optional[List[float]]:
    """
    분석 쿼리 텍스트의 벡터 임베딩을 생성합니다.
    프롬프트 기반 벡터 유사도 검색에 사용됩니다.
    
    Args:
        query_text: 임베딩을 생성할 쿼리 텍스트
    
    Returns:
        벡터 임베딩 리스트 (1536 차원) 또는 None (실패 시)
    """
    if not OPENAI_API_KEY:
        print("⚠️  OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. 쿼리 임베딩을 생성할 수 없습니다.")
        return None
    
    if not query_text or not query_text.strip():
        print("⚠️  빈 쿼리 텍스트로는 임베딩을 생성할 수 없습니다.")
        return None
    
    try:
        client = get_openai_client()
        if not client:
            return None
        
        # text-embedding-3-small 모델 사용 (1536 차원, news.py와 동일)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=query_text.strip()
        )
        
        embedding = response.data[0].embedding
        print(f"✅ 쿼리 임베딩 생성 완료: {len(embedding)} 차원")
        return embedding
    except Exception as e:
        import traceback
        print(f"⚠️  쿼리 임베딩 생성 실패: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None


def search_similar_news_by_embedding(
    db: Session,
    query_embedding: List[float],
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
    limit: int = 20
) -> List[NewsArticle]:
    """
    벡터 유사도 검색을 사용하여 날짜 범위 내에서 관련 뉴스를 조회합니다.
    날짜 필터링 후 벡터 유사도가 높은 순으로 정렬하여 상위 N개를 반환합니다.
    
    Args:
        db: 데이터베이스 세션
        query_embedding: 검색 쿼리 임베딩 (1536 차원)
        start_datetime: 시작 날짜/시간 (기본값: 전날 06:00:00)
        end_datetime: 종료 날짜/시간 (기본값: 현재 시간)
        limit: 반환할 최대 뉴스 개수 (기본값: 20)
    
    Returns:
        조회된 NewsArticle 객체 리스트 (유사도 순으로 정렬)
    """
    # 한국 시간대 설정
    seoul_tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(seoul_tz)
    
    # 기본값 설정: 전날 06:00 ~ 현재 시간
    if end_datetime is None:
        end_datetime = now
    else:
        if end_datetime.tzinfo is None:
            end_datetime = seoul_tz.localize(end_datetime)
    
    if start_datetime is None:
        yesterday = (now - timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
        start_datetime = yesterday
    else:
        if start_datetime.tzinfo is None:
            start_datetime = seoul_tz.localize(start_datetime)
    
    # ISO 형식으로 변환
    start_str = start_datetime.isoformat()
    end_str = end_datetime.isoformat()
    
    # 벡터를 PostgreSQL 배열 형식으로 변환
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
    
    try:
        sqlalchemy_conn = db.connection()
        raw_conn = None
        if hasattr(sqlalchemy_conn, 'connection'):
            raw_conn = sqlalchemy_conn.connection
            if hasattr(raw_conn, 'driver_connection'):
                raw_conn = raw_conn.driver_connection
        else:
            raw_conn = sqlalchemy_conn
        
        cursor = raw_conn.cursor()
        
        try:
            # 벡터 유사도 검색 (cosine distance 사용)
            # <=> 연산자는 cosine distance를 반환 (작을수록 유사함)
            cursor.execute("""
                SELECT id, embedding <=> %s::vector(1536) AS distance
                FROM news_articles
                WHERE embedding IS NOT NULL
                AND metadata IS NOT NULL
                AND metadata->>'published_date' IS NOT NULL
                AND (
                    (metadata->>'published_date')::timestamp >= %s::timestamp
                    AND (metadata->>'published_date')::timestamp <= %s::timestamp
                )
                ORDER BY embedding <=> %s::vector(1536)
                LIMIT %s
            """, (embedding_str, start_str, end_str, embedding_str, limit))
            
            article_ids = [row[0] for row in cursor.fetchall()]
            articles = db.query(NewsArticle).filter(NewsArticle.id.in_(article_ids)).all() if article_ids else []
            
            print(f"✅ 벡터 유사도 검색 완료: {len(articles)}개 (기간: {start_datetime.strftime('%Y-%m-%d %H:%M')} ~ {end_datetime.strftime('%Y-%m-%d %H:%M')}, 상위 {limit}개)")
            return articles
        finally:
            cursor.close()
        
    except Exception as e:
        import traceback
        print(f"⚠️  벡터 유사도 검색 실패: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"벡터 유사도 검색 중 오류가 발생했습니다: {e}")


def get_news_by_date_range(
    db: Session,
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
    query_embedding: Optional[List[float]] = None,
    limit: Optional[int] = None
) -> List[NewsArticle]:
    """
    벡터 DB에서 날짜 범위로 뉴스 기사를 조회합니다.
    query_embedding이 제공되면 벡터 유사도 검색을 사용하여 관련성이 높은 뉴스만 선택합니다.
    
    Args:
        db: 데이터베이스 세션
        start_datetime: 시작 날짜/시간 (기본값: 전날 06:00:00)
        end_datetime: 종료 날짜/시간 (기본값: 현재 시간)
        query_embedding: 검색 쿼리 임베딩 (제공 시 벡터 유사도 검색 사용)
        limit: 반환할 최대 뉴스 개수 (query_embedding 제공 시 기본값: 20, 없으면 None)
    
    Returns:
        조회된 NewsArticle 객체 리스트 (embedding이 있는 뉴스만)
    """
    # 벡터 유사도 검색 사용
    if query_embedding is not None:
        return search_similar_news_by_embedding(
            db=db,
            query_embedding=query_embedding,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            limit=limit if limit is not None else 20
        )
    
    # 기존 날짜 범위 검색 (벡터 유사도 없이)
    # 한국 시간대 설정
    seoul_tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(seoul_tz)
    
    # 기본값 설정: 전날 06:00 ~ 현재 시간
    if end_datetime is None:
        end_datetime = now
    else:
        # timezone이 없으면 seoul timezone 추가
        if end_datetime.tzinfo is None:
            end_datetime = seoul_tz.localize(end_datetime)
    
    if start_datetime is None:
        # 전날 06:00:00 계산
        yesterday = (now - timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
        start_datetime = yesterday
    else:
        # timezone이 없으면 seoul timezone 추가
        if start_datetime.tzinfo is None:
            start_datetime = seoul_tz.localize(start_datetime)
    
    # ISO 형식으로 변환 (metadata의 published_date 형식과 일치)
    start_str = start_datetime.isoformat()
    end_str = end_datetime.isoformat()
    
    # SQL 쿼리: embedding이 NULL이 아니고, metadata의 published_date가 범위 내인 뉴스 조회
    # metadata JSONB 필드에서 published_date 추출 및 필터링
    # published_date는 ISO 형식 문자열이므로 timestamp로 변환
    # psycopg2의 raw connection을 사용하여 %s 스타일 파라미터 바인딩 사용
    try:
        sqlalchemy_conn = db.connection()
        raw_conn = None
        if hasattr(sqlalchemy_conn, 'connection'):
            raw_conn = sqlalchemy_conn.connection
            if hasattr(raw_conn, 'driver_connection'):
                raw_conn = raw_conn.driver_connection
        else:
            raw_conn = sqlalchemy_conn
        
        cursor = raw_conn.cursor()
        
        try:
            # LIMIT 절 추가 (제공된 경우)
            limit_clause = f"LIMIT {limit}" if limit is not None else ""
            
            cursor.execute(f"""
                SELECT id FROM news_articles
                WHERE embedding IS NOT NULL
                AND metadata IS NOT NULL
                AND metadata->>'published_date' IS NOT NULL
                AND (
                    (metadata->>'published_date')::timestamp >= %s::timestamp
                    AND (metadata->>'published_date')::timestamp <= %s::timestamp
                )
                ORDER BY (metadata->>'published_date')::timestamp DESC
                {limit_clause}
            """, (start_str, end_str))
            
            article_ids = [row[0] for row in cursor.fetchall()]
            articles = db.query(NewsArticle).filter(NewsArticle.id.in_(article_ids)).all() if article_ids else []
            
            print(f"✅ 벡터 DB에서 뉴스 조회 완료: {len(articles)}개 (기간: {start_datetime.strftime('%Y-%m-%d %H:%M')} ~ {end_datetime.strftime('%Y-%m-%d %H:%M')})")
            return articles
        finally:
            cursor.close()
        
    except Exception as e:
        import traceback
        print(f"⚠️  벡터 DB 뉴스 조회 실패: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"벡터 DB에서 뉴스를 조회할 수 없습니다: {e}")


def analyze_news_with_ai(news_articles: List[NewsArticle]) -> Dict:
    """
    뉴스 기사들을 AI로 분석하여 파급효과, 산업, 주식을 예측합니다.
    LLM이 참조한 기사를 추적할 수 있도록 제목, URL, 발행일을 포함합니다.
    
    Args:
        news_articles: 분석할 뉴스 기사 리스트 (최대 20개까지 분석)
    
    Returns:
        분석 결과 딕셔너리. 다음 형식을 따릅니다:
        
        {
            "summary": str,  # 전체 뉴스 요약 및 주식 동향 분석 근거 (500~800자)
            "industries": [
                {
                    "industry_name": str,  # 산업명 (예: "반도체", "금융", "에너지" 등)
                    "impact_level": str,  # 영향 수준: "high" | "medium" | "low"
                    "impact_description": str,  # 해당 산업에 미치는 영향에 대한 상세 설명
                    "trend_direction": str,  # 트렌드 방향: "positive" | "negative" | "neutral"
                    "stocks": [
                        {
                            "stock_code": str,  # 종목코드 (6자리, 예: "005930")
                            "stock_name": str,  # 종목명 (예: "삼성전자")
                            "expected_trend": str,  # 예상 트렌드: "up" | "down" | "neutral"
                            "confidence_score": float,  # 신뢰도 점수 (0.0-1.0, 예: 0.85)
                            "reasoning": str  # 해당 주식의 예측 근거 및 분석 내용
                        }
                    ]
                }
            ]
        }
    
    분석 결과 상세 설명:
        - summary: 전체 뉴스 기사들을 종합한 요약 및 주식 동향 분석 근거 (500~800자)
          뉴스 기사들을 종합하여 주식 시장 전반의 동향을 분석하고, 주요 산업과 종목에 미치는 영향을
          구체적인 근거와 함께 설명합니다. 뉴스에서 언급된 구체적인 사건, 데이터, 정책 변화 등을
          바탕으로 주식 시장의 예상 움직임을 논리적으로 설명합니다.
        - industries: 산업별 분석 리스트
          - industry_name: 분석된 산업명 (예: 반도체, 금융, 에너지, IT, 자동차 등)
          - impact_level: 주식 시장에 미치는 영향 수준
            * "high": 높은 영향 (시장 변동성 크게 증가)
            * "medium": 중간 영향 (일부 변동성 증가)
            * "low": 낮은 영향 (미미한 영향)
          - impact_description: 해당 산업에 미치는 영향에 대한 상세 설명
          - trend_direction: 트렌드 방향
            * "positive": 긍정적 트렌드 (상승 예상)
            * "negative": 부정적 트렌드 (하락 예상)
            * "neutral": 중립적 트렌드 (변동 없음 예상)
          - stocks: 해당 산업의 주식 리스트
            * stock_code: 6자리 종목코드 (예: "005930" = 삼성전자)
            * stock_name: 종목명 (예: "삼성전자")
            * expected_trend: 예상 트렌드
              - "up": 상승 예상
              - "down": 하락 예상
              - "neutral": 중립 (변동 없음)
            * confidence_score: 신뢰도 점수 (0.0-1.0)
              - 0.9 이상: 매우 높은 신뢰도
              - 0.7-0.9: 높은 신뢰도
              - 0.5-0.7: 중간 신뢰도
              - 0.5 미만: 낮은 신뢰도
            * reasoning: 예측 근거 및 분석 내용
    
    Example:
        >>> result = analyze_news_with_ai(news_articles)
        >>> print(result["summary"])
        "반도체 산업 급등, 금융권 부진..."
        >>> 
        >>> # 첫 번째 산업 정보
        >>> industry = result["industries"][0]
        >>> print(industry["industry_name"])  # "반도체"
        >>> print(industry["impact_level"])    # "high"
        >>> print(industry["trend_direction"])  # "positive"
        >>> 
        >>> # 첫 번째 주식 정보
        >>> stock = industry["stocks"][0]
        >>> print(stock["stock_code"])  # "005930"
        >>> print(stock["stock_name"])  # "삼성전자"
        >>> print(stock["expected_trend"])  # "up"
        >>> print(stock["confidence_score"])  # 0.85
        >>> print(stock["reasoning"])  # "반도체 수요 증가로 인한..."
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
    
    # 뉴스 요약 (제목, URL, 발행일, 내용 포함)
    news_items = []
    for idx, article in enumerate(news_articles[:20], 1):  # 최대 20개까지 분석
        # metadata에서 정보 추출
        url = article.url or "URL 없음"
        published_date = "날짜 정보 없음"
        
        if article.article_metadata:
            metadata = article.article_metadata
            if isinstance(metadata, dict):
                url = metadata.get("url", article.url) or "URL 없음"
                published_date = metadata.get("published_date", "날짜 정보 없음")
        
        # published_at이 있으면 사용
        if article.published_at:
            published_date = article.published_at.strftime("%Y-%m-%d %H:%M:%S")
        
        content_preview = article.content[:500] if article.content else "내용 없음"
        
        news_items.append(f"""{idx}. 제목: {article.title}
   URL: {url}
   발행일: {published_date}
   내용: {content_preview}""")
    
    news_summary = "\n\n".join(news_items)
    
    prompt = f"""다음 뉴스 기사들을 분석하여 주식 시장에 미치는 영향을 분석해주세요.

뉴스 기사:
{news_summary}

다음 JSON 형식으로 응답해주세요:
{{
    "summary": "전체 뉴스 요약 및 주식 동향 분석 근거 (500~800자). 뉴스 기사들을 종합하여 주식 시장 전반의 동향을 분석하고, 주요 산업과 종목에 미치는 영향을 구체적인 근거와 함께 설명해주세요. 뉴스에서 언급된 구체적인 사건, 데이터, 정책 변화 등을 바탕으로 주식 시장의 예상 움직임을 논리적으로 설명해주세요.",
    "industries": [
        {{
            "industry_name": "산업명",
            "impact_level": "high|medium|low",
            "impact_description": "영향 설명",
            "trend_direction": "positive|negative|neutral",
            "stocks": [
                {{
                    "stock_code": "종목코드 (6자리)",
                    "stock_name": "종목명",
                    "expected_trend": "up|down|neutral",
                    "confidence_score": 0.0-1.0,
                    "reasoning": "예측 근거"
                }}
            ]
        }}
    ]
}}

한국 주식 시장에 집중하여 분석해주세요. 실제 존재하는 종목 코드와 이름을 사용해주세요.
각 뉴스 기사의 URL을 참조하여 정확한 정보를 바탕으로 분석해주세요.
summary 필드는 반드시 500자 이상 800자 이하로 작성해주세요."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 비용 절감을 위해 mini 모델 사용
            messages=[
                {"role": "system", "content": "당신은 주식 시장 분석 전문가입니다. 뉴스를 분석하여 주식 시장에 미치는 영향을 정확하게 예측합니다."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        return result
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 실패: {e}")
        print(f"응답 텍스트: {result_text if 'result_text' in locals() else 'N/A'}")
        raise ValueError(f"AI 분석 결과를 파싱할 수 없습니다: {e}")
    except Exception as e:
        import traceback
        print(f"OpenAI API 호출 실패: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise


def save_analysis_to_db(
    db: Session,
    news_articles: List[NewsArticle],
    analysis_result: Dict,
    analysis_date: date
) -> Report:
    """
    분석 결과를 데이터베이스에 저장합니다.
    
    Args:
        db: 데이터베이스 세션
        news_articles: 분석된 뉴스 기사 리스트
        analysis_result: AI 분석 결과
        analysis_date: 분석 날짜
    
    Returns:
        생성된 Report 객체
    """
    # Report 생성
    report = Report(
        title=f"{analysis_date.strftime('%Y-%m-%d')} 주식 동향 분석",
        summary=analysis_result.get("summary", ""),
        analysis_date=analysis_date
    )
    db.add(report)
    db.flush()  # ID를 얻기 위해 flush
    
    # 뉴스 연결
    for news in news_articles:
        report.news_articles.append(news)
    
    # 산업 및 주식 저장
    for industry_data in analysis_result.get("industries", []):
        industry = ReportIndustry(
            report_id=report.id,
            industry_name=industry_data.get("industry_name", ""),
            impact_level=industry_data.get("impact_level", "medium"),
            impact_description=industry_data.get("impact_description", ""),
            trend_direction=industry_data.get("trend_direction", "neutral")
        )
        db.add(industry)
        db.flush()
        
        # 주식 저장
        for stock_data in industry_data.get("stocks", []):
            stock = ReportStock(
                report_id=report.id,
                industry_id=industry.id,
                stock_code=stock_data.get("stock_code", ""),
                stock_name=stock_data.get("stock_name", ""),
                expected_trend=stock_data.get("expected_trend", "neutral"),
                confidence_score=float(stock_data.get("confidence_score", 0.5)),
                reasoning=stock_data.get("reasoning", "")
            )
            db.add(stock)
    
    db.commit()
    db.refresh(report)
    
    return report


def analyze_and_save(
    db: Session,
    news_articles: List[NewsArticle],
    analysis_date: Optional[date] = None
) -> Report:
    """
    뉴스를 분석하고 결과를 저장합니다.
    
    Args:
        db: 데이터베이스 세션
        news_articles: 분석할 뉴스 기사 리스트
        analysis_date: 분석 날짜 (기본값: 오늘)
    
    Returns:
        생성된 Report 객체
    """
    if not news_articles:
        raise ValueError("분석할 뉴스 기사가 없습니다.")
    
    if analysis_date is None:
        analysis_date = date.today()
    
    # AI 분석
    analysis_result = analyze_news_with_ai(news_articles)
    
    # 결과 저장
    report = save_analysis_to_db(db, news_articles, analysis_result, analysis_date)
    
    return report


def analyze_news_from_vector_db(
    db: Session,
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
    analysis_date: Optional[date] = None
) -> Report:
    """
    벡터 DB에서 날짜 범위로 뉴스를 조회하고, AI 분석을 수행하여 보고서를 생성합니다.
    벡터 유사도 검색을 사용하여 분석 프롬프트와 관련성이 높은 뉴스만 선택합니다.
    전체 플로우를 하나의 함수로 통합합니다.
    
    Args:
        db: 데이터베이스 세션
        start_datetime: 시작 날짜/시간 (기본값: 전날 06:00:00)
        end_datetime: 종료 날짜/시간 (기본값: 현재 시간)
        analysis_date: 분석 날짜 (기본값: 오늘)
    
    Returns:
        생성된 Report 객체
    
    Raises:
        ValueError: 뉴스가 없거나 분석 실패 시
    """
    # 분석 프롬프트 기반 쿼리 임베딩 생성
    # 주식 시장 동향 분석에 관련된 키워드로 쿼리 생성
    query_text = "주식 시장 동향 분석 산업별 영향 주식 예측"
    query_embedding = create_query_embedding(query_text)
    
    # 벡터 DB에서 뉴스 조회 (벡터 유사도 검색 사용)
    if query_embedding:
        news_articles = get_news_by_date_range(
            db=db,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            query_embedding=query_embedding,
            limit=20  # 상위 20개만 선택
        )
        print(f"✅ 벡터 유사도 검색으로 {len(news_articles)}개 뉴스 선택")
    else:
        # 쿼리 임베딩 생성 실패 시 기존 방식 사용
        print("⚠️  쿼리 임베딩 생성 실패, 날짜 범위 필터링만 사용")
        news_articles = get_news_by_date_range(
            db=db,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            limit=20
        )
    
    if not news_articles:
        raise ValueError(f"조회된 뉴스 기사가 없습니다. (기간: {start_datetime} ~ {end_datetime})")
    
    # 분석 및 저장
    report = analyze_and_save(db, news_articles, analysis_date)
    
    print(f"✅ 벡터 DB 기반 분석 완료: 보고서 ID={report.id}, 뉴스 {len(news_articles)}개 분석")
    
    return report
