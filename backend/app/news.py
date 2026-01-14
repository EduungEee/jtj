"""
뉴스 수집 모듈
여러 뉴스 API를 사용하여 최신 뉴스를 수집할 수 있도록 확장 가능한 아키텍처로 구성합니다.
"""
import json
import os
import sys
import math
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

import requests
from sqlalchemy.orm import Session

# models 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from models.models import NewsArticle

# ============================================================================
# 상수 정의
# ============================================================================

# API 설정
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")
NEWSDATA_API_URL = "https://newsdata.io/api/1/latest"
NEWSDATA_MAX_SIZE = 10  # newsdata.io 무료 티어 제한

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_API_URL = "https://openapi.naver.com/v1/search/news.json"
NAVER_MAX_SIZE = 100

NEWSORG_API_KEY = os.getenv("NEWSORG_API_KEY")
NEWSORG_API_URL = "https://newsapi.org/v2/everything"
NEWSORG_MAX_SIZE = 100

THENEWSAPI_API_KEY = os.getenv("THENEWSAPI_API_KEY")
THENEWSAPI_API_URL = "https://api.thenewsapi.com/v1/news/all"
THENEWSAPI_MAX_SIZE = 50  # 기본 제한

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDING_DIMENSION = 1536

# 요청 타임아웃 (초)
REQUEST_TIMEOUT = 10

# 날짜 파싱 형식
DATE_FORMAT_ISO = "%Y-%m-%dT%H:%M:%S"
DATE_FORMAT_RFC2822 = "%a, %d %b %Y %H:%M:%S %z"
DATE_FORMAT_RFC2822_NO_TZ = "%a, %d %b %Y %H:%M:%S"
DATE_FORMAT_SIMPLE = "%Y-%m-%d %H:%M:%S"

# ============================================================================
# 유틸리티 함수
# ============================================================================


def parse_datetime(date_str: str) -> Optional[datetime]:
    """
    다양한 형식의 날짜 문자열을 datetime 객체로 변환합니다.
    
    Args:
        date_str: 날짜 문자열
        
    Returns:
        datetime 객체 또는 None (파싱 실패 시)
    """
    if not date_str:
        return None
    
    # ISO 8601 형식 시도
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        pass
    
    # RFC 2822 형식 시도 (타임존 포함)
    try:
        return datetime.strptime(date_str, DATE_FORMAT_RFC2822)
    except ValueError:
        pass
    
    # RFC 2822 형식 시도 (타임존 없음)
    try:
        return datetime.strptime(date_str, DATE_FORMAT_RFC2822_NO_TZ)
    except ValueError:
        pass
    
    # 간단한 형식 시도
    try:
        return datetime.strptime(date_str, DATE_FORMAT_SIMPLE)
    except ValueError:
        print(f"⚠️  날짜 파싱 실패: {date_str}")
        return None


def clean_html_tags(text: str) -> str:
    """
    Naver API 응답에서 HTML 태그와 엔티티를 제거합니다.
    
    Args:
        text: HTML 태그가 포함된 텍스트
        
    Returns:
        정제된 텍스트
    """
    if not text:
        return ""
    
    replacements = {
        "<b>": "",
        "</b>": "",
        "&quot;": '"',
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
    }
    
    cleaned = text
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    
    return cleaned


def extract_domain_from_url(url: str) -> str:
    """
    URL에서 도메인을 추출합니다.
    
    Args:
        url: URL 문자열
        
    Returns:
        도메인 문자열 (추출 실패 시 빈 문자열)
    """
    if not url:
        return ""
    
    try:
        import tldextract
        extracted = tldextract.extract(url)
        return extracted.domain
    except Exception:
        return ""


def handle_api_error(e: Exception, api_name: str, response: Optional[requests.Response] = None) -> ValueError:
    """
    API 에러를 처리하고 상세한 에러 메시지를 반환합니다.
    
    Args:
        e: 발생한 예외
        api_name: API 이름
        response: HTTP 응답 객체 (있는 경우)
        
    Returns:
        ValueError 예외 객체
    """
    error_msg = f"{api_name} API 요청 실패: {str(e)}"
    
    if isinstance(e, requests.exceptions.HTTPError) and response:
        print(f"{api_name} API HTTP 오류: {e}")
        print(f"응답 상태 코드: {response.status_code}")
        print(f"응답 헤더: {dict(response.headers)}")
        
        try:
            error_data = response.json()
            print(f"응답 내용: {error_data}")
            
            # API별 에러 메시지 키 추출
            error_message = error_data.get("message") or error_data.get("errorMessage", "알 수 없는 오류")
            error_msg = f"{api_name} API 오류 ({response.status_code}): {error_message}"
        except Exception:
            print(f"응답 내용: {response.text}")
            error_msg = f"{api_name} API 오류 ({response.status_code}): {response.text}"
    
    print(f"Traceback: {traceback.format_exc()}")
    return ValueError(error_msg)


def get_raw_connection(db: Session):
    """
    SQLAlchemy 세션에서 raw PostgreSQL connection을 가져옵니다.
    
    Args:
        db: SQLAlchemy 세션
        
    Returns:
        raw PostgreSQL connection 객체
    """
    sqlalchemy_conn = db.connection()
    
    if hasattr(sqlalchemy_conn, 'connection'):
        raw_conn = sqlalchemy_conn.connection
        # SQLAlchemy 2.0+ 지원
        if hasattr(raw_conn, 'driver_connection'):
            raw_conn = raw_conn.driver_connection
        return raw_conn
    
    return sqlalchemy_conn


def normalize_provider_name(provider_name: str) -> str:
    """
    Provider 이름을 정규화합니다.
    
    Args:
        provider_name: Provider 이름 (예: "newsdata.io", "The News API")
        
    Returns:
        정규화된 Provider 이름 (예: "newsdata", "thenewsapi")
    """
    # Provider 이름 매핑
    provider_mapping = {
        "newsdata.io": "newsdata",
        "Naver": "naver",
        "The News API": "thenewsapi",
        "NewsAPI.org": "newsorg",
    }
    
    # 매핑에 있으면 사용, 없으면 소문자로 변환하고 공백/점 제거
    if provider_name in provider_mapping:
        return provider_mapping[provider_name]
    
    return provider_name.lower().replace(" ", "").replace(".", "")


# ============================================================================
# 뉴스 제공자 공통 헬퍼 함수
# ============================================================================


def _make_api_request(
    url: str,
    params: dict,
    headers: Optional[dict],
    provider_name: str,
    timeout: int = REQUEST_TIMEOUT
) -> dict:
    """
    공통 HTTP GET 요청 처리 함수.
    
    Args:
        url: API 엔드포인트 URL
        params: 쿼리 파라미터
        headers: HTTP 헤더 (Optional)
        provider_name: Provider 이름 (로깅용)
        timeout: 타임아웃 (초)
        
    Returns:
        파싱된 JSON 응답
        
    Raises:
        ValueError: API 호출 실패 시
    """
    try:
        print(f"📰 {provider_name} API 호출: params={params}")
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        print(f"요청 URL: {response.url}")
        print(f"응답 상태 코드: {response.status_code}")
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        response = getattr(e, 'response', None)
        raise handle_api_error(e, provider_name, response)
    except Exception as e:
        raise ValueError(f"{provider_name} API 요청 실패: {str(e)}")


def _build_standard_article(
    title: str,
    content: str,
    source: str,
    url: str,
    published_at: Optional[datetime]
) -> dict:
    """
    표준화된 뉴스 기사 딕셔너리를 생성합니다.
    
    Args:
        title: 기사 제목
        content: 기사 내용
        source: 출처
        url: 기사 URL
        published_at: 발행 날짜
        
    Returns:
        표준화된 기사 딕셔너리
    """
    return {
        "title": title,
        "content": content,
        "source": source,
        "url": url,
        "published_at": published_at,
    }


# ============================================================================
# 뉴스 제공자 인터페이스 및 구현
# ============================================================================


class BaseNewsProvider(ABC):
    """
    뉴스 제공자 공통 인터페이스.
    여러 뉴스 API를 동일한 형태의 결과로 반환하도록 추상화합니다.
    
    새 뉴스 API를 추가할 때는 이 클래스를 상속받아 구현하고,
    get_default_providers()에 등록하면 됩니다.
    """

    name: str = "base"
    supports_or: bool = True
    max_size: int = 10

    @abstractmethod
    def fetch(self, query: str, size: int) -> List[dict]:
        """
        뉴스를 수집해 표준화된 딕셔너리 리스트로 반환합니다.
        
        각 아이템은 다음 키를 포함해야 합니다:
        - title: str
        - content: str
        - source: str
        - url: str
        - published_at: Optional[datetime]
        
        Args:
            query: 검색 쿼리
            size: 가져올 뉴스 개수
            
        Returns:
            뉴스 기사 딕셔너리 리스트
        """
        raise NotImplementedError


class NewsdataProvider(BaseNewsProvider):
    """newsdata.io 기반 뉴스 제공자."""

    name = "newsdata.io"
    supports_or = True
    max_size = NEWSDATA_MAX_SIZE

    def fetch(self, query: str = "주식", size: int = 10) -> List[dict]:
        """
        newsdata.io API에서 최신 뉴스를 가져옵니다.
        
        Args:
            query: 검색 쿼리
            size: 가져올 뉴스 개수 (1-10, 무료 티어 제한)
        
        Returns:
            뉴스 기사 리스트
            
        Raises:
            ValueError: API 호출 실패 시
        """
        if not NEWSDATA_API_KEY:
            raise ValueError("NEWSDATA_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        if not (1 <= size <= NEWSDATA_MAX_SIZE):
            raise ValueError(f"size는 1-{NEWSDATA_MAX_SIZE} 사이의 값이어야 합니다. (무료 티어 제한) 현재 값: {size}")
        
        params = {
            "apikey": NEWSDATA_API_KEY,
            "q": query,
            "country": "kr",
            "language": "ko",
            "timezone": "asia/seoul",
            "image": 0,
            "video": 0,
            "removeduplicate": 1,
            "size": size,
        }
        
        try:
            # 422 에러 특별 처리를 위해 직접 요청 처리
            print(f"📰 {self.name} API 호출: query={query}, size={size}")
            response = requests.get(NEWSDATA_API_URL, params=params, timeout=REQUEST_TIMEOUT)
            print(f"요청 URL: {response.url}")
            print(f"응답 상태 코드: {response.status_code}")
            
            # 422 에러 특별 처리
            if response.status_code == 422:
                try:
                    error_data = response.json()
                    error_message = error_data.get("message", "파라미터 오류")
                    raise ValueError(f"newsdata.io API 파라미터 오류: {error_message}")
                except ValueError:
                    raise
                except Exception:
                    raise ValueError(f"newsdata.io API 파라미터 오류: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "success":
                error_message = data.get("message", "알 수 없는 오류")
                raise ValueError(f"newsdata.io API 오류: {error_message}")
            
            results = data.get("results", [])
            total_results = data.get("totalResults", 0)
            print(f"✅ API 응답 성공: 총 {total_results}개 결과, {len(results)}개 반환")
            
            articles = []
            for item in results:
                published_at = parse_datetime(item.get("pubDate", ""))
                articles.append(_build_standard_article(
                    title=item.get("title", ""),
                    content=item.get("description", ""),
                    source=item.get("source_id", ""),
                    url=item.get("link", ""),
                    published_at=published_at
                ))
            
            print(f"✅ 파싱된 뉴스 기사: {len(articles)}개")
            return articles
            
        except requests.exceptions.RequestException as e:
            response = getattr(e, 'response', None)
            raise handle_api_error(e, self.name, response)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"{self.name} API 요청 실패: {str(e)}")



class NaverProvider(BaseNewsProvider):
    """Naver 뉴스 검색 API 기반 뉴스 제공자."""

    name = "Naver"
    supports_or = False
    max_size = NAVER_MAX_SIZE

    def fetch(self, query: str = "주식", size: int = 10) -> List[dict]:
        """
        Naver 뉴스 검색 API에서 최신 뉴스를 가져옵니다.
        
        Args:
            query: 검색 쿼리
            size: 가져올 뉴스 개수 (1-100)
        
        Returns:
            뉴스 기사 리스트
            
        Raises:
            ValueError: API 호출 실패 시
        """
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            raise ValueError("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 환경 변수가 설정되지 않았습니다.")
        
        if not (1 <= size <= NAVER_MAX_SIZE):
            raise ValueError(f"size는 1-{NAVER_MAX_SIZE} 사이의 값이어야 합니다. 현재 값: {size}")
        
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        }
        
        params = {
            "query": query,
            "display": min(size, NAVER_MAX_SIZE),
            "sort": "date",
            "start": 1,
        }
        
        try:
            data = _make_api_request(NAVER_API_URL, params, headers, self.name)
            
            items = data.get("items", [])
            total_results = data.get("total", 0)
            print(f"✅ API 응답 성공: 총 {total_results}개 결과, {len(items)}개 반환")
            
            articles = []
            for item in items:
                title = clean_html_tags(item.get("title", ""))
                description = clean_html_tags(item.get("description", ""))
                originallink = item.get("originallink", "")
                link = item.get("link", "")
                url = originallink if originallink else link
                published_at = parse_datetime(item.get("pubDate", ""))
                
                # originallink에서 도메인 추출
                source = extract_domain_from_url(originallink) if originallink else ""
                
                articles.append(_build_standard_article(
                    title=title,
                    content=description,
                    source=source,
                    url=url,
                    published_at=published_at
                ))
            
            print(f"✅ 파싱된 뉴스 기사: {len(articles)}개")
            return articles
            
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"{self.name} API 요청 실패: {str(e)}")


class NewsOrgProvider(BaseNewsProvider):
    """NewsAPI.org 기반 뉴스 제공자."""

    name = "NewsAPI.org"
    supports_or = True
    max_size = NEWSORG_MAX_SIZE

    def fetch(self, query: str = "주식", size: int = 10) -> List[dict]:
        """
        NewsAPI.org (NewsOrg)에서 최신 뉴스를 가져옵니다.
        
        Args:
            query: 검색 쿼리
            size: 가져올 뉴스 개수 (1-100)
        
        Returns:
            뉴스 기사 리스트
            
        Raises:
            ValueError: API 호출 실패 시
        """
        if not NEWSORG_API_KEY:
            raise ValueError("NEWSORG_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        if not (1 <= size <= NEWSORG_MAX_SIZE):
            raise ValueError(f"size는 1-{NEWSORG_MAX_SIZE} 사이의 값이어야 합니다. 현재 값: {size}")
        
        params = {
            "apiKey": NEWSORG_API_KEY,
            "q": query,
            "pageSize": min(size, NEWSORG_MAX_SIZE),
            "sortBy": "publishedAt",
        }
        
        try:
            data = _make_api_request(NEWSORG_API_URL, params, None, self.name)
            
            if data.get("status") != "ok":
                error_message = data.get("message", "알 수 없는 오류")
                raise ValueError(f"NewsAPI.org API 오류: {error_message}")
                
            articles_data = data.get("articles", [])
            total_results = data.get("totalResults", 0)
            print(f"✅ API 응답 성공: 총 {total_results}개 결과, {len(articles_data)}개 반환")
            
            articles = []
            for item in articles_data:
                title = item.get("title", "")
                description = item.get("description", "")
                url = item.get("url", "")
                published_at = parse_datetime(item.get("publishedAt", ""))
                
                # source 정보 추출
                source_info = item.get("source", {})
                if isinstance(source_info, dict):
                    source = source_info.get("name", "")
                else:
                    source = str(source_info) if source_info else ""
                
                # source가 비어있으면 URL에서 도메인 추출
                if not source and url:
                    source = extract_domain_from_url(url)
                
                articles.append(_build_standard_article(
                    title=title,
                    content=description,
                    source=source,
                    url=url,
                    published_at=published_at
                ))
            
            print(f"✅ 파싱된 뉴스 기사: {len(articles)}개")
            return articles
            
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"{self.name} API 요청 실패: {str(e)}")




class TheNewsAPIProvider(BaseNewsProvider):
    """The News API 기반 뉴스 제공자."""

    name = "The News API"
    supports_or = True
    max_size = THENEWSAPI_MAX_SIZE

    def fetch(self, query: str = "주식", size: int = 10) -> List[dict]:
        """
        The News API에서 최신 뉴스를 가져옵니다.
        
        Args:
            query: 검색 쿼리
            size: 가져올 뉴스 개수 (1-50)
        
        Returns:
            뉴스 기사 리스트
            
        Raises:
            ValueError: API 호출 실패 시
        """
        if not THENEWSAPI_API_KEY:
            raise ValueError("THENEWSAPI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        if not (1 <= size <= THENEWSAPI_MAX_SIZE):
            raise ValueError(f"size는 1-{THENEWSAPI_MAX_SIZE} 사이의 값이어야 합니다. 현재 값: {size}")
        
        params = {
            "api_token": THENEWSAPI_API_KEY,
            "search": query,
            "language": "ko",
            "locale": "kr",
            "limit": min(size, THENEWSAPI_MAX_SIZE),
            "sort": "published_at",
        }
        
        try:
            data = _make_api_request(THENEWSAPI_API_URL, params, None, self.name)
            
            articles_data = data.get("data", [])
            meta = data.get("meta", {})
            found = meta.get("found", 0)
            print(f"✅ API 응답 성공: 총 {found}개 결과, {len(articles_data)}개 반환")
            
            articles = []
            for item in articles_data:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                description = item.get("description", "")
                content = snippet or description or ""
                url = item.get("url", "")
                published_at = parse_datetime(item.get("published_at", ""))
                
                # source 정보 추출
                source_info = item.get("source", {})
                if isinstance(source_info, dict):
                    source = source_info.get("name", "")
                else:
                    source = str(source_info) if source_info else ""
                
                # source가 비어있으면 URL에서 도메인 추출
                if not source and url:
                    source = extract_domain_from_url(url)
                
                articles.append(_build_standard_article(
                    title=title,
                    content=content,
                    source=source,
                    url=url,
                    published_at=published_at
                ))
            
            print(f"✅ 파싱된 뉴스 기사: {len(articles)}개")
            return articles
            
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"{self.name} API 요청 실패: {str(e)}")


def get_default_providers() -> List[BaseNewsProvider]:
    """
    활성화된 기본 뉴스 제공자 목록을 반환합니다.
    
    Returns:
        활성화된 Provider 리스트
    """
    providers: List[BaseNewsProvider] = []

    if NEWSDATA_API_KEY:
        providers.append(NewsdataProvider())

    if NAVER_CLIENT_ID and NAVER_CLIENT_SECRET:
        providers.append(NaverProvider())

    if NEWSORG_API_KEY:
        providers.append(NewsOrgProvider())

    if THENEWSAPI_API_KEY:
        providers.append(TheNewsAPIProvider())

    return providers


# ============================================================================
# 임베딩 및 메타데이터 생성
# ============================================================================


def create_embedding(text_content: str) -> Optional[List[float]]:
    """
    OpenAI Embedding API를 사용하여 텍스트의 벡터 임베딩을 생성합니다.
    
    Args:
        text_content: 임베딩을 생성할 텍스트
        
    Returns:
        벡터 임베딩 리스트 (1536 차원) 또는 None (실패 시)
    """
    if not OPENAI_API_KEY:
        print("⚠️  OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. 임베딩을 생성할 수 없습니다.")
        return None
    
    if not text_content or not text_content.strip():
        print("⚠️  빈 텍스트로는 임베딩을 생성할 수 없습니다.")
        return None
    
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=text_content.strip()
        )
        
        embedding = response.data[0].embedding
        print(f"✅ 임베딩 생성 완료: {len(embedding)} 차원")
        return embedding
        
    except Exception as e:
        print(f"⚠️  임베딩 생성 실패: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None


def create_metadata(
    title: str,
    url: str,
    published_at: Optional[datetime],
    collected_at: Optional[datetime]
) -> dict:
    """
    벡터 DB에 저장할 메타데이터를 생성합니다.
    LLM이 나중에 어떤 기사를 참조했는지 알 수 있도록 title과 url을 반드시 포함합니다.
    
    Args:
        title: 뉴스 기사 제목
        url: 뉴스 기사 URL
        published_at: 발행 날짜
        collected_at: 수집 날짜
        
    Returns:
        메타데이터 딕셔너리
    """
    metadata = {
        "title": title,
        "url": url,
    }
    
    if published_at:
        metadata["published_date"] = published_at.isoformat()
    
    if collected_at:
        metadata["collected_at"] = collected_at.isoformat()
    else:
        metadata["collected_at"] = datetime.now().isoformat()
    
    return metadata


# ============================================================================
# 데이터베이스 저장 함수
# ============================================================================


def save_embedding_to_db(
    db: Session,
    article_id: int,
    embedding: List[float],
    metadata: dict,
    commit: bool = False
) -> None:
    """
    pgvector에 벡터 임베딩을 저장합니다.
    
    Args:
        db: 데이터베이스 세션
        article_id: 뉴스 기사 ID
        embedding: 벡터 임베딩 리스트
        metadata: 메타데이터 딕셔너리
        commit: 커밋 여부 (기본값: False, 트랜잭션을 외부에서 관리할 때 사용)
        
    Raises:
        Exception: 벡터 저장 실패 시
    """
    try:
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"
        metadata_json = json.dumps(metadata, ensure_ascii=False)
        
        raw_conn = get_raw_connection(db)
        cursor = raw_conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE news_articles 
                SET embedding = %s::vector(1536),
                    metadata = %s::jsonb
                WHERE id = %s
            """, (embedding_str, metadata_json, article_id))
            
            if commit:
                raw_conn.commit()
            
            print(f"✅ 벡터 임베딩 저장 완료: article_id={article_id}")
        finally:
            cursor.close()
            
    except Exception as e:
        error_msg = str(e)
        if "SQL:" in error_msg:
            error_msg = error_msg.split("SQL:")[0].strip()
        
        print(f"⚠️  벡터 임베딩 저장 실패 (article_id={article_id}): {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        raise


def save_metadata_only(db: Session, article_id: int, metadata: dict) -> None:
    """
    메타데이터만 저장합니다 (임베딩 생성 실패 시 사용).
    
    Args:
        db: 데이터베이스 세션
        article_id: 뉴스 기사 ID
        metadata: 메타데이터 딕셔너리
    """
    metadata_json = json.dumps(metadata, ensure_ascii=False)
    raw_conn = get_raw_connection(db)
    cursor = raw_conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE news_articles 
            SET metadata = %s::jsonb
            WHERE id = %s
        """, (metadata_json, article_id))
    finally:
        cursor.close()
    
    print(f"✅ 메타데이터 저장 완료 (임베딩 없음): article_id={article_id}")


def save_news_to_db(db: Session, articles: List[dict]) -> List[NewsArticle]:
    """
    뉴스 기사를 데이터베이스에 저장합니다.
    중복 체크 (URL 기반)를 수행하고, 벡터 임베딩을 생성하여 pgvector에 저장합니다.
    벡터 저장이 실패하면 뉴스 기사 저장도 함께 롤백됩니다.
    
    Args:
        db: 데이터베이스 세션
        articles: 저장할 뉴스 기사 리스트
    
    Returns:
        저장된 NewsArticle 객체 리스트
    
    Raises:
        Exception: 벡터 저장 실패 시 뉴스 기사 저장도 롤백됨
    """
    saved_articles = []
    collected_at = datetime.now()
    
    try:
        # 1단계: 뉴스 기사 저장 (아직 commit하지 않음)
        for article_data in articles:
            url = article_data.get("url")
            if not url:
                continue
            
            # URL 기반 중복 체크
            existing = db.query(NewsArticle).filter(NewsArticle.url == url).first()
            if existing:
                continue
            
            news_article = NewsArticle(
                title=article_data.get("title", ""),
                content=article_data.get("content", ""),
                source=article_data.get("source", ""),
                url=url,
                published_at=article_data.get("published_at"),
                provider=article_data.get("provider", "")  # API 제공자 정보
            )
            
            db.add(news_article)
            saved_articles.append(news_article)
        
        # flush하여 ID를 얻기 (아직 commit하지 않음)
        db.flush()
        
        # 저장된 객체에 ID 부여를 위해 refresh
        for article in saved_articles:
            db.refresh(article)
        
        # 2단계: 벡터 임베딩 생성 및 저장
        for article in saved_articles:
            # 해당 article의 원본 데이터 찾기
            article_data = next(
                (a for a in articles if a.get("url") == article.url),
                None
            )
            
            if not article_data:
                continue
            
            metadata = create_metadata(
                title=article_data.get("title", ""),
                url=article_data.get("url", ""),
                published_at=article_data.get("published_at"),
                collected_at=collected_at
            )
            
            # 임베딩 생성
            content = article_data.get("content", "")
            embedding = create_embedding(content)
            
            if embedding:
                save_embedding_to_db(
                    db=db,
                    article_id=article.id,
                    embedding=embedding,
                    metadata=metadata,
                    commit=False
                )
            else:
                save_metadata_only(db, article.id, metadata)
        
        # 3단계: 모든 작업이 성공하면 commit
        db.commit()
        print(f"✅ 뉴스 수집 및 벡터 저장 완료: {len(saved_articles)}개 저장됨")
        return saved_articles
        
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        if "SQL:" in error_msg:
            error_msg = error_msg.split("SQL:")[0].strip()
        print(f"⚠️  뉴스 저장 실패 (전체 롤백): {error_msg}")
        raise

def _fetch_from_provider_safe(
    provider: BaseNewsProvider, 
    queries: List[str], 
    size: int
) -> List[dict]:
    """
    Provider에서 뉴스를 안전하게 수집합니다. (예외 처리 포함)
    
    Args:
        provider: 뉴스 Provider 객체
        queries: 검색 쿼리 리스트
        size: 가져올 뉴스 개수
        
    Returns:
        수집된 뉴스 기사 리스트 (실패 시 빈 리스트)
    """
    # Provider 특성에 따른 쿼리 변환
    if provider.supports_or:
        transformed_query = " OR ".join(queries)
    else:
        transformed_query = queries[0]
    
    try:
        print(f"▶ 뉴스 수집: provider={provider.name}, query={transformed_query}, target_size={size} (Fair Share)")
        provider_articles = provider.fetch(query=transformed_query, size=size)

        # Provider 이름을 정규화하고 각 article에 추가
        provider_name_normalized = normalize_provider_name(provider.name)
        
        for article in provider_articles:
            article["provider"] = provider_name_normalized
            if not article.get("source"):
                article["source"] = provider.name
        
        num_fetched = len(provider_articles)
        print(f"✅ {provider.name}에서 {num_fetched}개 기사를 가져왔습니다.")
        return provider_articles
        
    except Exception as e:
        # 개별 Provider 실패는 로그만 남기고 계속 진행
        print(f"⚠️  뉴스 제공자 '{provider.name}' 수집 실패: {e}")
        return []


# ============================================================================
# 메인 수집 함수
# ============================================================================


def collect_news(db: Session, query: str = "주식", size: int = 10) -> List[NewsArticle]:
    """
    (멀티 Provider 아키텍처) 뉴스를 수집하고 데이터베이스에 저장합니다.
    
    여러 뉴스 API Provider를 통해 뉴스를 수집한 뒤,
    URL 기준 중복 제거는 DB 저장 함수(save_news_to_db)에서 처리합니다.
    
    요구사항:
    - query에 ',' 단위로 여러 값을 주면 각 api 특성에 맞게 OR 연산자로 query를 변환.
    - 연산자를 지원하지 않는 api는 맨 앞의 쿼리만 적용.
    - 필요한 총 뉴스 갯수에 맞추어서 api에게 긁어올 뉴스 갯수를 할당.
    - 균등 분배(Fair Distribution) 및 부족분 채우기(Deficit Filling):
      - 남은 필요한 개수를 남은 API 개수로 나누어 할당 (올림 처리).
      - 각 API는 할당된 양과 자신의 max_size 중 작은 값을 시도.
      - 가져온 만큼 remaining_size를 줄여서, 다음 API가 부족분을 동적으로 더 가져오게 됨.
    
    Args:
        db: 데이터베이스 세션
        query: 검색 쿼리
        size: 전체적으로 가져올 목표 뉴스 개수 (기본값: 10개)
    
    Returns:
        저장된 NewsArticle 객체 리스트
    
    Raises:
        ValueError: API 호출 실패 또는 뉴스 수집 실패 시
    """
    try:
        providers = get_default_providers()
        if not providers:
            raise ValueError("사용 가능한 뉴스 제공자가 없습니다. API 키 설정을 확인해주세요.")

        # 쿼리 분리
        queries = [q.strip() for q in query.split(",") if q.strip()]
        if not queries:
            queries = ["주식"]

        collected_articles: List[dict] = []
        
        # 모든 Provider에서 가능한 최대 개수 수집
        for provider in providers:
            # 각 Provider의 최대 한도만큼 요청
            allocated_size = provider.max_size
            
            # Provider에서 뉴스 수집
            provider_articles = _fetch_from_provider_safe(
                provider=provider,
                queries=queries,
                size=allocated_size
            )
            
            if provider_articles:
                collected_articles.extend(provider_articles)

        if not collected_articles:
            raise ValueError(
                f"'{query}' 검색어로 뉴스를 찾을 수 없습니다. "
                f"다른 검색어를 시도하거나 Provider 구성을 확인해주세요."
            )

        # 데이터베이스에 저장 (URL 기반 중복 제거 포함)
        # 이미 중복된 뉴스가 제외될 수 있으므로, 최종 반환된 저장 뉴스 개수가 size보다 적을 수 있음
        saved_articles = save_news_to_db(db, collected_articles)

        print(f"✅ 뉴스 수집 완료 (멀티 Provider): {len(saved_articles)}개 최종 저장됨")
        return saved_articles
        
    except ValueError:
        raise
    except Exception as e:
        print(f"⚠️  뉴스 수집 중 예상치 못한 오류: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"뉴스 수집 실패: {str(e)}")
