"""
AI 분석 모듈
Gemini API를 사용하여 뉴스를 분석하고 산업/주식 예측을 수행합니다.
"""
import os
import json
import csv
import re
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
import google.generativeai as genai
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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini 클라이언트 초기화
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def _safe_json_loads(value: object) -> Optional[dict]:
    """
    안전하게 JSON 문자열을 dict로 변환합니다.

    Args:
        value: dict 또는 JSON 문자열(또는 그 외 타입)

    Returns:
        dict 또는 None
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
    return None


def _normalize_analysis_result(analysis_result: Dict) -> Dict:
    """
    LLM 응답 스키마가 일부 누락/변형되어도 후속 로직(DB 저장/응답)이 깨지지 않도록 정규화합니다.

    - industries / impact_description / buy|hold|sell_candidates 누락 시 기본값을 채웁니다.
    - buy|hold|sell_candidates 내부의 stocks를 industry.stocks로 펼쳐 저장 로직에서 누락되지 않게 합니다.
    """
    if not isinstance(analysis_result, dict):
        return {"summary": "", "industries": []}

    analysis_result.setdefault("summary", "")
    industries = analysis_result.get("industries")
    if not isinstance(industries, list):
        industries = []
        analysis_result["industries"] = industries

    trend_default_by_bucket = {
        "buy_candidates": "up",
        "hold_candidates": "neutral",
        "sell_candidates": "down",
    }

    for industry in industries:
        if not isinstance(industry, dict):
            continue

        impact_desc = _safe_json_loads(industry.get("impact_description")) or {}
        market_summary = impact_desc.get("market_summary")
        if not isinstance(market_summary, dict):
            impact_desc["market_summary"] = {"market_sentiment": "", "key_themes": []}
        else:
            market_summary.setdefault("market_sentiment", "")
            if not isinstance(market_summary.get("key_themes"), list):
                market_summary["key_themes"] = []

        for bucket in ("buy_candidates", "hold_candidates", "sell_candidates"):
            if not isinstance(impact_desc.get(bucket), list):
                impact_desc[bucket] = []

        industry["impact_description"] = impact_desc

        # 기존 stocks가 없거나 비어있을 때, impact_description 후보군의 stocks를 펼쳐 채움
        existing_stocks = industry.get("stocks")
        if not isinstance(existing_stocks, list):
            existing_stocks = []

        flattened: list[dict] = []
        seen: set[tuple[str, str, str]] = set()

        for bucket in ("buy_candidates", "hold_candidates", "sell_candidates"):
            groups = impact_desc.get(bucket, [])
            if not isinstance(groups, list):
                continue
            for group in groups:
                if not isinstance(group, dict):
                    continue
                group_stocks = group.get("stocks", [])
                if not isinstance(group_stocks, list):
                    continue
                for stock in group_stocks:
                    if not isinstance(stock, dict):
                        continue
                    stock_code = str(stock.get("stock_code", "") or "")
                    stock_name = str(stock.get("stock_name", "") or "")
                    expected_trend = str(
                        stock.get("expected_trend", trend_default_by_bucket[bucket]) or trend_default_by_bucket[bucket]
                    )
                    key = (stock_code, stock_name, expected_trend)
                    if key in seen:
                        continue
                    seen.add(key)
                    reasoning = str(stock.get("reasoning", "") or "")
                    if reasoning and not reasoning.startswith("["):
                        reasoning = f"[{bucket}] {reasoning}"

                    confidence_score = stock.get("confidence_score", 0.5)
                    try:
                        confidence_score = float(confidence_score)
                    except Exception:
                        confidence_score = 0.5

                    flattened.append(
                        {
                            "stock_code": stock_code,
                            "stock_name": stock_name,
                            "expected_trend": expected_trend,
                            "confidence_score": confidence_score,
                            "reasoning": reasoning,
                        }
                    )

        # 기존 stocks가 이미 있으면 유지하되, 부족하면 flatten 결과를 뒤에 덧붙임
        if isinstance(existing_stocks, list) and existing_stocks:
            industry["stocks"] = existing_stocks
        else:
            industry["stocks"] = flattened

        # 필드 기본값
        industry.setdefault("industry_name", "")
        industry.setdefault("impact_level", "medium")
        industry.setdefault("trend_direction", "neutral")

    return analysis_result


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

    system_prompt = """
당신은 장기투자 관점의 주식 리서치 애널리스트이자 포트폴리오 매니저다.

역할:
- 투자 기간: 최소 3년 이상의 장기투자.
- 스타일: 성장성과 재무 건전성을 중시하는 Bottom-up + Top-down 혼합.
- 목표: 지난 24시간 뉴스에 기반해
  1) 새로 매수할 유망 산업군과 종목
  2) 기존 보유 시 계속 보유할 유망 산업군과 종목
  3) 단계적 매도를 고려해야 할 산업군과 종목
  을 식별하고, 그 근거를 요약해 제시한다.
- 추가 목표: 뉴스에서 드러난 1차적(직접) 수혜/피해뿐 아니라,
  공급망, 고객 산업, 경쟁 산업, 대체재·보완재 관점에서
  2차·3차로 파급되는 산업/종목까지 구조적으로 예측한다.

제한사항:
- 단기 뉴스 모멘텀만으로 매수/매도 결정을 내리지 말고, 장기 구조적 성장 가능성과 리스크를 함께 평가하라.
- 과도하게 공격적이거나 투기적인 표현(“무조건 오른다” 등)은 금지한다.
- 뉴스에 존재하지 않는 사실을 단정적으로 만들어내지 말고,
  연쇄 시나리오도 '합리적인 추론' 수준에서만 제시하고,
  불확실성이 크면 reasoning에 그 사실을 명시하라.
- 신뢰도(confidence_score)가 낮은 경우(예: 0.4 미만)에는
  구체적인 매수/매도보다는 관찰·모니터링 대상으로 서술하라.
- reasoning의 첫 문장은 반드시 impact_chain_level과 propagation_path 범위를 명시한다.
- impact_chain_level보다 높은 단계(예: 1차 종목에서 2차·3차 영향)는
  reasoning과 propagation_path 어디에도 언급하지 않는다.

연쇄 영향 분석 기준 (필수):
1) 1차 영향 (confidence_score ≥ 0.7 필수)
   - 뉴스에 직접 언급된 산업/종목
   - 또는 뉴스에서 드러난 사건이 매출/이익에 직접 연결되는 주체
   - 예: "삼성전자 반도체 매출 호조" → 삼성전자 (1차)

2) 2차 영향 (confidence_score ≥ 0.5 필수) 
   - 1차 영향의 핵심 공급업체/고객/파트너
   - 공급망 비중이 크거나, 역사적 상관관계가 명확한 경우만
   - 예: 삼성전자 반도체 호조 → SK하이닉스 HBM (2차, 실제 고객사임)

3) 3차 영향 (confidence_score ≥ 0.3, 선택적)
   - 2차 영향의 공급업체/고객 또는 인프라/자본재
   - 역사적 사례나 명확한 경제적 연결고리가 있을 때만
   - 예: HBM 수요 증가 → 포토닉스/소재 업체 (3차)

출력 필수 규칙:
- 최소 1개의 1차 + 1개의 2차 영향은 반드시 제시하라
- 3차는 신뢰도 ≥ 0.3이고 논리적 연결고리가 명확할 때만 추가
- 각 단계별 confidence_score는 다음 기준으로 부여하라:
  | 단계 | 최소 신뢰도 | 뉴스 직접성 | 역사적 사례 |
  |------|-------------|-------------|-------------|
  | 1차  | ≥ 0.7      | 직접 언급  | 필요 없음  |
  | 2차  | ≥ 0.5      | 간접 언급  | 있으면 +0.1|
  | 3차  | ≥ 0.3      | 추론       | 있으면 +0.1|


출력 형식:
- 반드시 유효한 JSON만 출력하라.
- JSON 이외의 설명, 자연어 문장, 마크다운은 출력하지 마라.
- 아래 스키마를 정확히 따르라.

JSON 스키마:
{
  "summary": "아래 산업 분석에는 전체 시장 요약, 투자 전략(Buy/Hold/Sell), 연쇄 영향 시나리오가 포함되어 있습니다.",

  "industries": [
    {
      "industry_name": "시장 종합 및 투자 전략",
      "impact_level": "high" | "medium" | "low",
      "trend_direction": "positive" | "negative" | "neutral",

      "impact_description": {
        "market_summary": {
          "market_sentiment": "positive" | "negative" | "neutral",
          "key_themes": ["string"]
        },

        "buy_candidates": [
          {
            "industry": "string",
            "reason_industry": "string",
            "stocks": [
              {
                "stock_code": "string",
                "stock_name": "string",
                "expected_trend": "up",
                "confidence_score": 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0,
                "impact_chain_level": 1 | 2 | 3,
                "propagation_path": [
                {
                    "level": 1,
                    "details": [
                        "1차: 뉴스 직접 언급 → [구체적 사건]",
                        "투자 논리: [매출/이익 영향 경로]",
                        "신뢰도 근거: [뉴스 직접성/수치 명시]",
                    ]
                },
                {
                    "level": 2,
                    "details": [
                        "1차: [1차 산업/종목] 수요/공급 변화",
                        "2차: [공급망 연결고리] → 본 종목 영향", 
                        "신뢰도 근거: [역사적 사례/매출 비중/고객사 명시]",
                    ]
                },
                {
                    "level": 3,
                    "details": [
                        "1차: [1차 사건]",
                        "2차: [2차 산업 영향]", 
                        "3차: [인프라/후행 수혜] → 본 종목",
                        "신뢰도 근거: [과거 유사 사례/투자 사이클]",
                    ]
                }
                ],
                "reasoning": "string",
                "news_drivers": ["string"],
                "risk_factors": ["string"]
              }
            ]
          }
        ],

        "hold_candidates": [
          {
            "industry": "string",
            "reason_industry": "string",
            "stocks": [
              {
                "stock_code": "string",
                "stock_name": "string",
                "expected_trend": "neutral",
                "confidence_score": 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0,
                "impact_chain_level": 1 | 2 | 3,
                "propagation_path": [
                {
                    "level": 1,
                    "details": [
                        "1차: 뉴스 직접 언급 → [구체적 사건]",
                        "투자 논리: [매출/이익 영향 경로]",
                        "신뢰도 근거: [뉴스 직접성/수치 명시]",
                    ]
                },
                {
                    "level": 2,
                    "details": [
                        "1차: [1차 산업/종목] 수요/공급 변화",
                        "2차: [공급망 연결고리] → 본 종목 영향", 
                        "신뢰도 근거: [역사적 사례/매출 비중/고객사 명시]",
                    ]
                },
                {
                    "level": 3,
                    "details": [
                        "1차: [1차 사건]",
                        "2차: [2차 산업 영향]", 
                        "3차: [인프라/후행 수혜] → 본 종목",
                        "신뢰도 근거: [과거 유사 사례/투자 사이클]",
                    ]
                }
                ],
                "reasoning": "string",
                "news_drivers": ["string"],
                "risk_factors": ["string"]
              }
            ]
          }
        ],

        "sell_candidates": [
          {
            "industry": "string",
            "reason_industry": "string",
            "stocks": [
              {
                "stock_code": "string",
                "stock_name": "string",
                "expected_trend": "down",
                "confidence_score": 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0,
                "impact_chain_level": 1 | 2 | 3,
                "propagation_path": [
                {
                    "level": 1,
                    "details": [
                        "1차: 뉴스 직접 언급 → [구체적 사건]",
                        "투자 논리: [매출/이익 영향 경로]",
                        "신뢰도 근거: [뉴스 직접성/수치 명시]",
                    ]
                },
                {
                    "level": 2,
                    "details": [
                        "1차: [1차 산업/종목] 수요/공급 변화",
                        "2차: [공급망 연결고리] → 본 종목 영향", 
                        "신뢰도 근거: [역사적 사례/매출 비중/고객사 명시]",
                    ]
                },
                {
                    "level": 3,
                    "details": [
                        "1차: [1차 사건]",
                        "2차: [2차 산업 영향]", 
                        "3차: [인프라/후행 수혜] → 본 종목",
                        "신뢰도 근거: [과거 유사 사례/투자 사이클]",
                    ]
                }
                ],
                "reasoning": "string",
                "news_drivers": ["string"],
                "risk_factors": ["string"]
              }
            ]
          }
        ]
      },

      "stocks": []
    }
  ]
}

시장과 개별 종목의 관계 규칙:

1) 시장 분위기(market_sentiment)의 역할
- "market_sentiment"는 지수·시장 전반의 위험 선호/회피 상황을 나타낸다.
- 이는 개별 종목의 단기 수급과 밸류에이션에 영향을 주지만,
  모든 종목에 동일 방향의 결론을 강제로 적용하지 않는다.

2) 역행 사례 허용 (중요)
- 시장이 부정적이더라도, 구조적으로 성장성이 크거나
  펀더멘털이 개선되는 소수 종목은 "up" 또는 "보유/추가 매수" 판단을 내릴 수 있다.
- 반대로 시장이 긍정적이더라도, 경쟁력 약화·규제·수요 감소 등으로
  장기 전망이 나쁜 종목은 "down" 또는 "매도/비중 축소" 판단을 내릴 수 있다.
- 이러한 '시장과 반대 방향' 판단을 하는 경우,
  reasoning에서 반드시 다음 두 가지를 모두 설명해야 한다.
  1) 시장 전체와 다른 결론을 내린 이유 (종목의 특수 요인)
  2) 시장 분위기가 이 종목에 미치는 제한적 영향 또는 리스크

3) reasoning 내용 구조
- expected_trend가 "up"이면서 market_sentiment가 "부정적"인 경우:
  - 장기 펀더멘털·구조적 성장 요인 → 왜 시장과 달리 좋게 보는지
  - 다만, 전체 시장이 부정적이라 단기 변동성·하락 리스크가 존재함을 함께 언급
- expected_trend가 "down"이면서 market_sentiment가 "긍정적"인 경우:
  - 산업 구조 변화, 경쟁 심화, 규제, 일회성 호재 소멸 등
    종목 고유의 악재를 중심으로 설명
  - 시장이 좋더라도 이 종목에는 왜 지속적으로 불리한지 서술

4) 일관성 검증 규칙
- 모델은 각 종목별로 다음을 스스로 점검해야 한다.
  - market_sentiment와 expected_trend가 다른 방향일 경우,
    reasoning 안에 '시장 vs 종목' 관점의 설명이 포함되어 있는지 확인한다.
  - 만약 그런 설명이 없다면, reasoning을 수정하여
    시장과 종목의 관계를 명시적으로 설명한다.
"""
    
    prompt_header = f"""아래는 지난 24시간 동안 수집된 뉴스 기사들이다.
각 기사는 날짜, 제목, 본문, (존재한다면) 관련 종목 코드/종목명을 포함하고 있다.
이 뉴스들을 분석하여, 위에서 제시한 JSON 스키마에 정확히 맞는 하나의 JSON 객체를 출력하라.

[뉴스_데이터_시작]
{news_summary}
[뉴스_데이터_끝]

propagation_path 출력 규칙 (필수):

- propagation_path에는 impact_chain_level 이하의 단계만 포함한다.
- impact_chain_level = 1 인 경우:
  → propagation_path에는 level 1만 포함하고, level 2·3은 절대 출력하지 않는다.
- impact_chain_level = 2 인 경우:
  → propagation_path에는 level 1, level 2까지만 포함하고 level 3은 출력하지 않는다.
- impact_chain_level = 3 인 경우:
  → propagation_path에는 level 1, level 2, level 3을 모두 포함할 수 있다.
- 위 규칙을 어길 경우 출력은 무효로 간주한다.

주의:
- summary는 약 500~800자 분량으로 작성하되, JSON 구조를 깨지 않는 것을 최우선으로 한다.
- industries 배열은 최소 1개 이상 포함하되, 의미 있는 산업만 넣는다.
- 종목 코드가 불명확하면 "stock_code": "" 로 두고, reasoning에 그 이유를 적는다.
- 유효한 JSON만 출력하고, 그 외 어떤 텍스트도 출력하지 않는다.
- propagation_path 배열의 길이는 impact_chain_level 값과 정확히 일치해야 한다.
    - 예: impact_chain_level = 1 → propagation_path 길이 = 1

추가 요구사항:
- 각 종목의 reasoning에는 반드시 다음 세 가지가 모두 포함되도록 하라.
  1) 1차/2차/3차 중 어느 단계의 영향인지 (impact_chain_level에 1, 2, 3으로 표시)
  2) 영향이 전이되는 구체적 경로(propagation_path 배열에 단계별로 한국어로 서술)
  3) 해당 시나리오에 대한 신뢰도(confidence_score 값과, 왜 그 정도 신뢰도를 부여했는지에 대한 설명)

- 예시:
  - 엔비디아 GPU 수요 급증 뉴스가 있을 경우,
    엔비디아: impact_chain_level = 1, 직접 수혜.
    HBM 공급업체(SK하이닉스 등): impact_chain_level = 2, GPU 업체의 부품 수요 전이.
    HBM 소재/장비 업체: impact_chain_level = 3, 메모리 투자 확대의 후행 수혜.
  - 이와 같이 한 산업의 변화가 밸류체인 상에서 어떻게 확산되는지
    최소 1개 이상의 구체적인 연쇄 시나리오를 작성하라.

- 신뢰도가 낮은 경우(confidence_score < 0.4)에는
  reasoning에서 "시나리오 불확실성 높음", "추가 데이터 필요" 등으로 명시하고,
  매수/매도보다는 관찰·모니터링 대상으로 설명하라.

- 시장 분위기(market_sentiment)가 부정적이더라도, 일부 종목은 구조적으로 강한 성장성이나 실적 개선 요인으로 인해 "up" 또는 "보유" 판단을 내릴 수 있다.
- 반대로 시장 분위기가 긍정적이더라도, 특정 종목은 경쟁력 약화, 규제, 수요 감소 등으로 인해 "down" 또는 "매도" 판단을 내릴 수 있다.
- 이러한 시장과 반대 방향의 판단을 내리는 경우,
  reasoning 안에 반드시
  "시장 전체 분위기"와 "해당 종목의 개별 요인"을 비교하여 설명하라.

- reasoning 작성 템플릿 (반드시 이 구조를 따르라):
"[impact_chain_level]차 영향 | [propagation_path 요약] | 신뢰도[confidence_score]: [신뢰도 근거]

장점: [구체적 호재/수혜 요인]
리스크: [시장/경쟁/규제 리스크]
결론: [buy/hold/sell 판단 + 시장 분위기 고려]"
    
예시:
"2차 영향 | GPU 수요→HBM 수요 전이 | 신뢰도0.7: 엔비디아 실제 고객사
 
장점: HBM 고마진·고수율로 이익 개선 기대
리스크: 글로벌 경기 둔화로 데이터센터 투자 지연 가능성  
결론: 시장 부정적이나 HBM 구조적 수요로 보유 적정"
"""

    # 실제 작동 예시는 f-string 바깥의 일반 문자열로 분리하여
    # 중괄호({})를 포함하더라도 포맷 에러가 발생하지 않도록 처리
    example_block = """

실제 작동 예시 (패턴 복사 금지, 구조만 학습):

뉴스: "삼성전자 HBM 매출 3배 증가, AI 서버 수요 급증"

1차: 삼성전자 (000660)
json
{
    "impact_chain_level": 1,
    "propagation_path": [
        "1차: HBM 매출 3배 증가 직접 언급",
        "투자 논리: 반도체 부문 실적 개선",
        "신뢰도 근거: 뉴스 수치 직접 명시"
    ],
    "confidence_score": 0.9,
    "reasoning": "1차 영향 | HBM 매출 3배 직접 확인 | 신뢰도0.9: 뉴스 수치 명시\\n\\n장점: HBM 고마진으로 반도체 이익률 대폭 개선\\n리스크: 메모리 사이클 하단 가능성\\n결론: 시장 변동성 존재하나 1차 수혜로 강력 매수"
}

2차: SK하이닉스 (000660) 
json
{
    "impact_chain_level": 2,
    "propagation_path": [
        "1차: 삼성전자 HBM 매출 3배 증가",
        "2차: HBM 시장 1위 SK하이닉스 수혜",
        "신뢰도 근거: HBM 시장점유율 50% 이상"
    ],
    "confidence_score": 0.8,
    "reasoning": "2차 영향 | 삼성전자 HBM→시장 전체 수요 확대 | 신뢰도0.8: 시장 1위\\n\\n장점: HBM 선단공정 경쟁력으로 점유율 확대\\n리스크: 가격 경쟁 심화 가능성\\n결론: 시장 조정에도 구조적 수요로 보유/추가매수"
}

3차: 후공정 장비 (예: 한미반도체)
json
{
    "impact_chain_level": 3,
    "propagation_path": [
        "1차: 삼성전자 HBM 생산 확대",
        "2차: SK하이닉스 HBM 생산 확대",
        "3차: 후공정 장비 투자 증가",
        "신뢰도 근거: HBM 생산 증가시 장비 수요 동반 증가"
    ],
    "confidence_score": 0.5,
    "reasoning": "3차 영향 | HBM 생산→장비 투자 | 신뢰도0.5: 사이클 의존도\\n\\n장점: HBM 생산 증가시 후공정 수혜\\n리스크: 투자 시점 불확실, 사이클 의존도 높음\\n결론: 관찰 후 2차 확인시 진입 고려"
}
"""

    prompt = prompt_header + example_block

    # Gemini 모델 사용
    model = genai.GenerativeModel('gemini-2.5-flash')
    full_prompt = f"{system_prompt}\n\n{prompt}"
    
    response = model.generate_content(
        full_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2
        )
    )

    result_text = response.text
    
    # 마크다운 코드 블록 제거 (```json ... ``` 형태)
    cleaned_text = result_text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_text)
        cleaned_text = re.sub(r'\n?```\s*$', '', cleaned_text)

    try:
        parsed = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM JSON 파싱 실패\n{e}\n\n원본 응답:\n{result_text}"
        )

    # 후속 DB 저장 로직 보호용 정규화
    parsed = _normalize_analysis_result(parsed)

    # 원본 텍스트도 같이 보존 (디버깅/재현용)
    parsed["result_text"] = result_text

    return parsed



def validate_prediction_with_ai(
    prediction_output: Dict,
    original_news: str,
    financial_data: str
) -> Dict:
    """
    예측 LLM의 산업/종목 추천을 뉴스와 재무제표 기준으로 검증합니다.
    
    Args:
        prediction_output: analyze_news_with_ai 함수의 출력 결과
        original_news: 원본 뉴스 텍스트
        financial_data: 재무제표 데이터 (JSON 문자열 또는 텍스트)
    
    Returns:
        검증 결과 딕셔너리
    """
    client = get_openai_client()
    if not client:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
    
    # prediction_output을 JSON 문자열로 변환
    if isinstance(prediction_output, dict):
        prediction_output_str = json.dumps(prediction_output, ensure_ascii=False, indent=2)
    else:
        prediction_output_str = str(prediction_output)
    
    system_prompt = """
당신은 장기투자 관점의 주식 분석 검증 전문가다. 예측 LLM의 산업/종목 추천을 뉴스와 재무제표 기준으로 엄격히 검증하라.

## 검증 역할 (필수 2단계 순차 수행)

### 1단계: 뉴스-산업/종목 일치성 검증 (예측 LLM 출력 vs 원본 뉴스)
**목표**: 예측 LLM이 뉴스 흐름을 왜곡/과장하지 않았는지 확인
**검증 기준**:
[OK] 뉴스 직접 언급 or 명확한 1차 영향 (confidence ≥0.7)
[OK] 논리적 2차 영향 (공급망/고객 연결 명확, confidence ≥0.5)
[X] 뉴스와 무관한 종목 (추론 과도)
[X] 뉴스 방향과 반대 추천 (예: 부정 뉴스→up 추천)
[X] 과도한 3차 영향 (연결고리 희박)
**출력**: 불일치 산업/종목 목록

[보수 원칙]
- 뉴스와 산업/종목의 연결이 억지스럽거나,
  단순 테마 연상에 불과하다고 판단되면
  confidence가 높더라도 가차 없이 news_mismatch로 분류한다.
- 검증 LLM은 예측 LLM의 낙관적 해석을 교정하는 역할임을 명심한다.

### 2단계: 재무 건전성 검증 (추천 종목 대상)
**우선순위 순 적용** (자기자본비율 → 부채비율 → 유동비율):
자기자본비율 <30%: [위험] 경기 충격 취약 → 매수/보유 부적합
부채비율 >200%: [위험] 재무구조 취약 → 장기투자 리스크
유동비율 <1.0: [위험] 단기 유동성 위기 가능성

**건전성 등급**:
- A: 모든 지표 양호 (자기자본≥30%, 부채≤200%, 유동≥1.5)
- B: 1개 지표 경계 (보수적 관찰)
- C: 2개 지표 위험 (보유 검토)
- D: 1개 지표 심각 (매도 검토) (자기자본<30% OR 부채>200% OR 유동<1.0)
- F: 2개 이상 심각 (매수 금지) (자기자본<25% OR 부채>250% OR 유동<0.8)
(우선순위는 "해석 및 설명 시 강조 순서"이며, 등급 판정 자체는 OR 조건을 기준으로 한다.)

[현금흐름 보조 점검]
- 잉여현금흐름(Free Cash Flow)이 지속적으로 음수인 경우,
  등급이 C 이상이라도 financial_soundness 평가를 한 단계 하향할 수 있다.
- 단, 본 프롬프트는 FCF를 단독 FAIL 조건으로 사용하지 않으며,
  재무 구조 리스크를 보강하는 참고 지표로만 활용한다.

## 출력 제한: 적합하지 않은 것만 선정
- 뉴스 일치성 완벽하고 재무 A/B등급 → 빈 배열 []
- **선정 이유 필수**: 왜 이 산업/종목이 부적합한지 구체적 근거

## 검증 출력 형식 (유효 JSON만 출력)
{
  "validation_summary": "검증 결과 요약: 뉴스 불일치 X개, 재무위험 Y개 종목 식별됨.",
  
  "news_mismatch": [
    {
      "industry": "예측 산업명",
      "stocks": ["종목코드1", "종목코드2"],
      "mismatch_reason": "구체적 불일치 사유 (뉴스 직접성 부족/방향 반대 등)",
      "evidence": "원본 뉴스에서 확인된 사실",
      "confidence_score": 0.7
    }
  ],
  
  "financial_risks": [
    {
      "stock_code": "종목코드",
      "stock_name": "종목명",
      "financial_metrics": {
        "self_equity_ratio": "XX%",
        "debt_ratio": "XXX%",
        "current_ratio": "X.X"
      },
      "health_grade": "A|B|C|D|F",
      "risk_priority": "자기자본|부채|유동",
      "recommendation": "매수금지|보유검토|관찰",
      "prediction_category": "buy|hold|sell"
    }
  ],
  
  "overall_assessment": {
    "news_accuracy": "high|medium|low",
    "financial_soundness": "high|medium|low",
    "total_reliable_stocks": 5,
    "total_risky_stocks": 3,
    "action_required": "즉시 수정|관찰|양호"
  }
}

mismatch_reason에 반드시 다음 중 하나를 명시:
- 산업 레벨 불일치
- 종목 레벨 불일치
- 산업은 맞으나 종목 연결 과도
"""

    prompt = f"""
[예측_LLM_출력]
{prediction_output_str}
[예측_LLM_출력_끝]

[원본_뉴스]
{original_news}
[원본_뉴스_끝]

[재무제표_데이터]
{financial_data}
[재무제표_데이터_끝]

## 검증 원칙 (반드시 준수)

### 뉴스 불일치 판정 기준
1. **직접성 부족**: 뉴스에 전혀 언급없는데 1차 영향 주장 [X]
2. **방향 반대**: 부정 뉴스인데 up/confidence≥0.7 [X]  
3. **과도 추론**: 3차 영향에 confidence≥0.5 [X]
4. **사실 왜곡**: 뉴스 수치/사건과 다른 해석 [X]

### 재무 위험 판정 기준 (우선순위 엄수)
CRITICAL (F등급):
자기자본비율 <25% OR 부채비율 >250% OR 유동비율 <0.8

HIGH RISK (D등급):
자기자본비율 <30% OR 부채비율 >200% OR 유동비율 <1.0

MONITOR (C등급):
자기자본비율 30~35% OR 부채비율 150~200% OR 유동비율 1.0~1.2

### edge case 처리
- 예측 LLM confidence <0.4: 자동으로 news_mismatch 제외 (이미 관찰권고)
- 재무 데이터 누락: financial_risks에서 제외, "데이터부족" 명시
- 시장 반대 방향 추천: reasoning에서 시장상황 고려했는지 확인 후 판단
- '턴어라운드 기대', '흑자전환 가능성'은 뉴스에 명확한 수치·계약·구조조정 결과가 없는 한 재무 위험을 상쇄하는 근거로 사용하지 않는다.

## 출력 제한사항
- news_mismatch: 실제 불일치만 (예측이 정확하면 빈 배열 [])
- financial_risks: C/D/F등급만 (A/B는 양호로 간주)
- confidence_score: 0.1단위, 뉴스 직접성에 따라 0.3~1.0
- reasoning 생략: JSON 구조 엄수, 자연어 설명 금지
- 시장 반대 방향 추천의 경우, evidence 필드에 "뉴스 vs 추천 방향"의 사실 관계만 기재

유효한 JSON만 출력. 다른 어떤 텍스트도 출력하지 마라.
"""

    # Gemini 모델 사용
    model = genai.GenerativeModel('gemini-2.5-flash')
    full_prompt = f"{system_prompt}\n\n{prompt}"
    
    response = model.generate_content(
        full_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.3  # 검증은 보수적으로
        )
    )

    result_text = response.text

    # response = client.chat.completions.create(
    #     model="gpt-4o-mini",  # 비용 절감을 위해 mini 모델 사용
    #     messages=[
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": prompt}
    #     ],
    #     response_format={"type": "json_object"},
    #     temperature=0.2
    # )

    # # LLM 원본 텍스트
    # result_text = response.choices[0].message.content
    
    # 마크다운 코드 블록 제거 (```json ... ``` 형태)
    cleaned_text = result_text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_text)
        cleaned_text = re.sub(r'\n?```\s*$', '', cleaned_text)

    try:
        parsed = json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"검증 LLM JSON 파싱 실패\n{e}\n\n원본 응답:\n{result_text}"
        )

    # 원본 텍스트 보존
    parsed["result_text"] = result_text

    return parsed


def build_news_summary_from_csv(csv_path: str) -> str:
    """
    현대자동차 크롤링 CSV 파일을 읽어 news_summary 형식의 문자열로 변환합니다.
    (제목, URL, 기재일만 사용하며, 내용은 제목으로 대체합니다.)
    """
    news_items: List[str] = []

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, 1):
            title = (row.get("제목") or "").strip()
            url = (row.get("URL") or "").strip() or "URL 없음"
            published_date = (row.get("기재일") or "").strip() or "날짜 정보 없음"

            # CSV에는 본문이 없어, 일단 제목을 내용 프리뷰로 사용
            content_preview = title or "내용 없음"

            news_items.append(
                f"""{idx}. 제목: {title}
   URL: {url}
   발행일: {published_date}
   내용: {content_preview}"""
            )

    return "\n\n".join(news_items)


class _CsvArticle:
    """CSV 데이터를 analyze_news_with_ai에서 사용하는 필드만 가진 간단한 기사 객체로 변환하기 위한 클래스."""

    def __init__(self, title: str, url: str, published_date: str):
        self.title = title
        self.url = url
        # analyze_news_with_ai가 기대하는 최소 메타데이터 구조
        self.article_metadata = {"url": url, "published_date": published_date}
        self.published_at = None
        # CSV에는 본문이 없어, 제목을 내용 프리뷰로 사용
        self.content = title


def build_articles_from_csv(csv_path: str) -> List[_CsvArticle]:
    """
    현대자동차 크롤링 CSV를 읽어 analyze_news_with_ai에 넣을 수 있는
    간단한 기사 객체 리스트로 변환합니다.
    """
    articles: List[_CsvArticle] = []

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("제목") or "").strip()
            url = (row.get("URL") or "").strip() or "URL 없음"
            published_date = (row.get("기재일") or "").strip() or "날짜 정보 없음"
            if not title and not url:
                continue
            articles.append(_CsvArticle(title=title, url=url, published_date=published_date))

    return articles



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
        # impact_description이 딕셔너리인 경우 JSON 문자열로 변환
        impact_desc = industry_data.get("impact_description", "")
        if isinstance(impact_desc, dict):
            impact_desc = json.dumps(impact_desc, ensure_ascii=False)
        elif not isinstance(impact_desc, str):
            impact_desc = str(impact_desc)
        
        # trend_direction 값 정규화 (up/down -> positive/negative)
        trend_direction = industry_data.get("trend_direction", "neutral")
        if trend_direction == "up":
            trend_direction = "positive"
        elif trend_direction == "down":
            trend_direction = "negative"
        
        industry = ReportIndustry(
            report_id=report.id,
            industry_name=industry_data.get("industry_name", ""),
            impact_level=industry_data.get("impact_level", "medium"),
            impact_description=impact_desc,
            trend_direction=trend_direction
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
) -> Tuple[Report, str]:
    """
    뉴스를 분석하고 결과를 저장합니다.
    
    Args:
        db: 데이터베이스 세션
        news_articles: 분석할 뉴스 기사 리스트
        analysis_date: 분석 날짜 (기본값: 오늘)
    
    Returns:
        (생성된 Report 객체, LLM이 생성한 원본 result_text) 튜플
    """
    if not news_articles:
        raise ValueError("분석할 뉴스 기사가 없습니다.")
    
    if analysis_date is None:
        analysis_date = date.today()
    
    # AI 분석
    analysis_result = analyze_news_with_ai(news_articles)
    
    # result_text 추출
    result_text = analysis_result.get("result_text", "")
    
    # 결과 저장
    report = save_analysis_to_db(db, news_articles, analysis_result, analysis_date)
    
    return report, result_text


def analyze_news_from_vector_db(
    db: Session,
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
    analysis_date: Optional[date] = None
) -> Tuple[Report, str]:
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
        (생성된 Report 객체, LLM이 생성한 원본 result_text) 튜플
    
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
    report, result_text = analyze_and_save(db, news_articles, analysis_date)
    
    print(f"✅ 벡터 DB 기반 분석 완료: 보고서 ID={report.id}, 뉴스 {len(news_articles)}개 분석")
    
    return report, result_text

if __name__ == "__main__":
    # 로컬에서 실행 시 현대자동차 크롤링 CSV를 읽어 요약 포맷과
    # LLM 분석 결과(JSON)를 둘 다 터미널에서 확인할 수 있도록 합니다.
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(base_dir, "현대자동차크롤링.csv")

    # 1) CSV 기반 news_summary 포맷 출력 (프롬프트에 들어가는 원본 텍스트 확인용)
    summary_text = build_news_summary_from_csv(csv_file)
    print("===== CSV 기반 news_summary =====")
    print(summary_text)
    print("\n===== LLM 분석 결과(JSON) =====")

    # 2) CSV를 기사 객체 리스트로 변환 후, 기존 analyze_news_with_ai 재사용
    csv_articles = build_articles_from_csv(csv_file)
    try:
        analysis_result = analyze_news_with_ai(csv_articles)
    except Exception as e:
        print(f"LLM 분석 중 오류가 발생했습니다: {e}")
        raise

    if not isinstance(analysis_result, dict):
        print(f"분석 결과 형식이 dict가 아닙니다. type={type(analysis_result)} value={analysis_result!r}")
    else:
        # 모델이 생성한 원본 JSON 텍스트가 result_text에 들어있으면 우선 출력
        result_text = analysis_result.get("result_text")
        if isinstance(result_text, str) and result_text.strip():
            print(result_text)
        else:
            # result_text가 없으면 파싱된 dict를 pretty JSON으로 출력
            print(json.dumps(analysis_result, ensure_ascii=False, indent=2))
        
        # 3) 검증 LLM 실행 (1분 10초 대기 후)
        # import time
        # wait_seconds = 70  # 1분 10초
        # print(f"\n⏳ 검증 LLM 실행까지 {wait_seconds}초 대기 중...")
        # time.sleep(wait_seconds)
        
        print("\n===== 검증 LLM 결과(JSON) =====")
        try:
            validation_result = validate_prediction_with_ai(
                prediction_output=analysis_result,
                original_news=summary_text,
                financial_data="재무제표 데이터 없음 (테스트용)"
            )
            validation_text = validation_result.get("result_text")
            if isinstance(validation_text, str) and validation_text.strip():
                print(validation_text)
            else:
                print(json.dumps(validation_result, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"검증 LLM 실행 중 오류가 발생했습니다: {e}")
