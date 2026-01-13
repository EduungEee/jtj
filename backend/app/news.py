"""
뉴스 수집 모듈
newsdata.io API를 사용하여 최신 뉴스를 수집합니다.
"""
import os
import requests
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
import sys
import os as os_module

# models 경로 추가
backend_path = os_module.path.dirname(os_module.path.dirname(os.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from models.models import NewsArticle

NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")
NEWSDATA_API_URL = "https://newsdata.io/api/1/latest"


def fetch_news_from_api(query: str = "주식", size: int = 10) -> List[dict]:
    """
    newsdata.io API에서 최신 뉴스를 가져옵니다.
    
    Args:
        query: 검색 쿼리 (기본값: "주식")
        size: 가져올 뉴스 개수 (1-10, 기본값: 10개, 무료 티어 제한)
    
    Returns:
        뉴스 기사 리스트
    """
    if not NEWSDATA_API_KEY:
        raise ValueError("NEWSDATA_API_KEY 환경 변수가 설정되지 않았습니다.")
    
    # size 범위 검증 (newsdata.io API 무료 티어: 1-10)
    if size < 1 or size > 10:
        raise ValueError(f"size는 1-10 사이의 값이어야 합니다. (무료 티어 제한) 현재 값: {size}")
    
    # newsdata.io API 파라미터 설정 (한국 관련 뉴스)
    params = {
        "apikey": NEWSDATA_API_KEY,
        "q": query,
        "country": "kr",  # 한국
        "language": "ko",  # 한국어
        "timezone": "asia/seoul",  # 한국 시간대 (소문자)
        "image": 0,  # 이미지 제외
        "video": 0,  # 비디오 제외
        "removeduplicate": 1,  # 중복 제거
        "size": size,  # 가져올 뉴스 개수
        # full_content는 무료 티어에서 지원하지 않으므로 제거
    }
    
    try:
        print(f"newsdata.io API 호출: query={query}, size={size}")
        print(f"요청 파라미터: {params}")
        response = requests.get(NEWSDATA_API_URL, params=params, timeout=10)
        
        # 응답 상태 확인
        print(f"응답 상태 코드: {response.status_code}")
        print(f"요청 URL: {response.url}")
        
        # 422 에러인 경우 상세 응답 로깅
        if response.status_code == 422:
            try:
                error_data = response.json()
                print(f"422 에러 상세 응답: {error_data}")
                error_message = error_data.get("message", "파라미터 오류")
                raise ValueError(f"newsdata.io API 파라미터 오류: {error_message}")
            except:
                print(f"422 에러 응답 텍스트: {response.text}")
                raise ValueError(f"newsdata.io API 파라미터 오류: {response.text}")
        
        response.raise_for_status()
        data = response.json()
        
        # newsdata.io API 응답 형식 확인
        if data.get("status") != "success":
            error_message = data.get("message", "알 수 없는 오류")
            raise ValueError(f"newsdata.io API 오류: {error_message}")
        
        total_results = data.get("totalResults", 0)
        results = data.get("results", [])
        
        print(f"API 응답 성공: 총 {total_results}개 결과, {len(results)}개 반환")
        
        articles = []
        for item in results:
            title = item.get("title", "")
            description = item.get("description", "")
            url = item.get("link", "")
            source_id = item.get("source_id", "")
            
            # pubDate 파싱 (ISO 8601 형식 또는 다른 형식)
            published_at = None
            pub_date_str = item.get("pubDate", "")
            if pub_date_str:
                try:
                    # ISO 8601 형식 파싱 시도
                    # 예: "2024-01-15T10:30:00Z" 또는 "2024-01-15T10:30:00+09:00"
                    published_at = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                except ValueError:
                    try:
                        # RFC 2822 형식 시도
                        published_at = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
                    except ValueError:
                        try:
                            # 다른 형식 시도
                            published_at = datetime.strptime(pub_date_str, "%Y-%m-%d %H:%M:%S")
                        except:
                            print(f"날짜 파싱 실패: {pub_date_str}")
                            pass
            
            articles.append({
                "title": title,
                "content": description,  # description을 content로 사용
                "source": source_id,  # source_id를 source로 사용
                "url": url,
                "published_at": published_at
            })
        
        print(f"파싱된 뉴스 기사: {len(articles)}개")
        return articles
    except requests.exceptions.HTTPError as e:
        import traceback
        print(f"newsdata.io API HTTP 오류: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"응답 상태 코드: {e.response.status_code}")
            print(f"응답 헤더: {dict(e.response.headers)}")
            try:
                error_data = e.response.json()
                print(f"응답 내용: {error_data}")
                error_message = error_data.get("message", "알 수 없는 오류")
                raise ValueError(f"newsdata.io API 오류 ({e.response.status_code}): {error_message}")
            except:
                print(f"응답 내용: {e.response.text}")
        print(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"newsdata.io API 요청 실패: {str(e)}")
    except requests.exceptions.RequestException as e:
        import traceback
        print(f"newsdata.io API 요청 실패: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"newsdata.io API 요청 실패: {str(e)}")


def save_news_to_db(db: Session, articles: List[dict]) -> List[NewsArticle]:
    """
    뉴스 기사를 데이터베이스에 저장합니다.
    중복 체크 (URL 기반)를 수행합니다.
    
    Args:
        db: 데이터베이스 세션
        articles: 저장할 뉴스 기사 리스트
    
    Returns:
        저장된 NewsArticle 객체 리스트
    """
    saved_articles = []
    
    for article_data in articles:
        # URL 기반 중복 체크
        existing = db.query(NewsArticle).filter(
            NewsArticle.url == article_data.get("url")
        ).first()
        
        if existing:
            continue
        
        # NewsArticle 생성
        news_article = NewsArticle(
            title=article_data.get("title", ""),
            content=article_data.get("content", ""),
            source=article_data.get("source", ""),
            url=article_data.get("url", ""),
            published_at=article_data.get("published_at")
        )
        
        db.add(news_article)
        saved_articles.append(news_article)
    
    db.commit()
    
    # 저장된 객체에 ID 부여를 위해 refresh
    for article in saved_articles:
        db.refresh(article)
    
    return saved_articles


def collect_news(db: Session, query: str = "주식", size: int = 10) -> List[NewsArticle]:
    """
    뉴스를 수집하고 데이터베이스에 저장합니다.
    
    Args:
        db: 데이터베이스 세션
        query: 검색 쿼리
        size: 가져올 뉴스 개수 (기본값: 10개, 무료 티어 제한)
    
    Returns:
        저장된 NewsArticle 객체 리스트
    
    Raises:
        ValueError: API 호출 실패 또는 뉴스 수집 실패 시
    """
    try:
        # API에서 뉴스 가져오기
        articles = fetch_news_from_api(query=query, size=size)
        
        if not articles:
            raise ValueError(f"'{query}' 검색어로 뉴스를 찾을 수 없습니다. 다른 검색어를 시도해주세요.")
        
        # 데이터베이스에 저장
        saved_articles = save_news_to_db(db, articles)
        
        print(f"뉴스 수집 완료: {len(saved_articles)}개 저장됨")
        return saved_articles
    except ValueError as e:
        # ValueError는 그대로 전달
        raise
    except Exception as e:
        import traceback
        print(f"뉴스 수집 중 예상치 못한 오류: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"뉴스 수집 실패: {str(e)}")
