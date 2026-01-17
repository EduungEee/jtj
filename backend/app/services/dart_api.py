"""
DART API 서비스
전자공시시스템(DART) OpenAPI를 사용하여 재무제표 데이터를 조회합니다.
"""
import os
import requests
from typing import Dict, Optional, List
from datetime import datetime
import time
import sys
import copy
import json
import zipfile
from io import BytesIO
import xml.etree.ElementTree as ET

# models 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from sqlalchemy.orm import Session
from models.models import FinancialStatement


DART_API_KEY = os.getenv("DART_API_KEY")
DART_API_BASE_URL = "https://opendart.fss.or.kr/api"

# stock_code -> dart_code 매핑 테이블 캐시
_stock_to_dart_mapping: Optional[Dict[str, str]] = None


def get_financial_statements(
    corp_code: str,
    bsns_year: Optional[str] = None,
    reprt_code: str = "11011"  # 11011: 사업보고서, 11012: 반기보고서, 11013: 분기보고서
) -> Optional[Dict]:
    """
    DART API를 통해 재무제표 데이터를 조회합니다.
    
    Args:
        corp_code: DART 기업코드 (8자리)
        bsns_year: 사업연도 (YYYY 형식, 기본값: 최근 연도)
        reprt_code: 보고서 코드 (기본값: 11011 - 사업보고서)
    
    Returns:
        재무제표 데이터 딕셔너리 또는 None (실패 시)
    """
    if not DART_API_KEY:
        print("⚠️  DART_API_KEY 환경 변수가 설정되지 않았습니다.")
        return None
    
    if not corp_code or len(corp_code) != 8:
        print(f"⚠️  잘못된 DART 코드: {corp_code}")
        return None
    
    # 기본값: 최근 연도
    if not bsns_year:
        bsns_year = str(datetime.now().year - 1)
    
    url = f"{DART_API_BASE_URL}/fnlttSinglAcnt.json"
    
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": "CFS"  # CFS: 연결재무제표, OFS: 별도재무제표
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == "000":  # 정상
            return data
        else:
            error_msg = data.get("message", "알 수 없는 오류")
            print(f"⚠️  DART API 오류: {error_msg} (corp_code: {corp_code})")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️  DART API 요청 실패: {e} (corp_code: {corp_code})")
        return None
    except Exception as e:
        print(f"⚠️  DART API 처리 실패: {e} (corp_code: {corp_code})")
        return None


def parse_financial_data(dart_data: Dict) -> Dict:
    """
    DART API 응답 데이터를 파싱하여 필요한 재무 지표를 추출합니다.
    
    Args:
        dart_data: DART API 응답 데이터
    
    Returns:
        파싱된 재무 데이터 딕셔너리
    """
    if not dart_data or not dart_data.get("list"):
        return {}
    
    financial_items = {}
    
    # 필요한 계정과목 매핑
    account_mapping = {
        "매출액": "revenue",
        "영업이익": "operating_profit",
        "당기순이익": "net_income",
        "자산총계": "total_assets",
        "부채총계": "total_debt",
        "자본총계": "equity",
        "유동자산": "current_assets",
        "유동부채": "current_liabilities"
    }
    
    for item in dart_data.get("list", []):
        account_nm = item.get("account_nm", "")
        thstrm_amount = item.get("thstrm_amount", "0")  # 당기금액
        frmtrm_amount = item.get("frmtrm_amount", "0")  # 전기금액
        
        # 계정과목이 매핑에 있는 경우
        for korean_name, english_name in account_mapping.items():
            if korean_name in account_nm:
                try:
                    amount = int(thstrm_amount.replace(",", "")) if thstrm_amount else 0
                    prev_amount = int(frmtrm_amount.replace(",", "")) if frmtrm_amount else 0
                    
                    financial_items[english_name] = amount
                    
                    # 성장률 계산 (매출액, 영업이익, 당기순이익)
                    if english_name in ["revenue", "operating_profit", "net_income"] and prev_amount > 0:
                        growth_key = f"{english_name}_growth"
                        financial_items[growth_key] = ((amount - prev_amount) / prev_amount) * 100
                    
                except (ValueError, AttributeError):
                    pass
                break
    
    return financial_items


def get_company_financials(
    dart_code: str,
    stock_code: Optional[str] = None
) -> Optional[Dict]:
    """
    회사의 재무제표 데이터를 조회하고 파싱합니다.
    
    Args:
        dart_code: DART 기업코드 (8자리)
        stock_code: 종목코드 (6자리, 선택사항)
    
    Returns:
        파싱된 재무 데이터 딕셔너리 또는 None
    """
    if not dart_code:
        return None
    
    # API 호출 제한을 고려하여 짧은 대기
    time.sleep(0.1)
    
    dart_data = get_financial_statements(dart_code)
    
    if not dart_data:
        return None
    
    financial_data = parse_financial_data(dart_data)
    
    # 추가 계산 지표
    if financial_data.get("revenue") and financial_data.get("operating_profit"):
        financial_data["operating_margin"] = (financial_data["operating_profit"] / financial_data["revenue"]) * 100
    
    if financial_data.get("total_assets") and financial_data.get("total_debt"):
        financial_data["debt_ratio"] = (financial_data["total_debt"] / financial_data["total_assets"]) * 100
    
    if financial_data.get("current_assets") and financial_data.get("current_liabilities"):
        financial_data["current_ratio"] = financial_data["current_assets"] / financial_data["current_liabilities"] if financial_data["current_liabilities"] > 0 else 0
    
    if financial_data.get("equity") and financial_data.get("total_assets"):
        financial_data["equity_ratio"] = (financial_data["equity"] / financial_data["total_assets"]) * 100
    
    return financial_data


def get_financial_from_db(db: Session, stock_code: str, dart_code: str, bsns_year: str) -> Optional[Dict]:
    """
    DB에서 재무제표를 조회합니다.
    
    Args:
        db: 데이터베이스 세션
        stock_code: 종목코드
        dart_code: DART 기업코드
        bsns_year: 사업연도 (YYYY 형식)
    
    Returns:
        재무 데이터 딕셔너리 또는 None
    """
    if not db or not stock_code or not dart_code or not bsns_year:
        return None
    
    try:
        financial_stmt = db.query(FinancialStatement).filter(
            FinancialStatement.stock_code == stock_code,
            FinancialStatement.dart_code == dart_code,
            FinancialStatement.bsns_year == bsns_year
        ).first()
        
        if financial_stmt and financial_stmt.financial_data:
            # 딕셔너리를 deep copy하여 반환 (참조 공유 방지)
            return copy.deepcopy(financial_stmt.financial_data)
        return None
    except Exception as e:
        print(f"⚠️  DB 조회 실패 ({stock_code}, {dart_code}, {bsns_year}): {e}")
        return None


def save_financial_to_db(
    db: Session,
    stock_code: str,
    dart_code: str,
    bsns_year: str,
    financial_data: Dict
) -> bool:
    """
    재무제표를 DB에 저장합니다.
    
    Args:
        db: 데이터베이스 세션
        stock_code: 종목코드
        dart_code: DART 기업코드
        bsns_year: 사업연도 (YYYY 형식)
        financial_data: 재무 데이터 딕셔너리
    
    Returns:
        저장 성공 여부
    """
    if not db or not stock_code or not dart_code or not bsns_year or not financial_data:
        return False
    
    try:
        # 딕셔너리를 JSON 문자열로 변환 후 다시 파싱하여 완전히 새로운 객체 생성
        # 이렇게 하면 SQLAlchemy의 mutable 객체 참조 문제를 완전히 해결
        financial_data_json = json.dumps(financial_data, ensure_ascii=False)
        financial_data_final = json.loads(financial_data_json)
        
        # 디버깅: 저장 전 데이터 확인
        revenue = financial_data_final.get("revenue", 0)
        print(f"💾 저장 시도: stock_code={stock_code}, dart_code={dart_code}, bsns_year={bsns_year}, revenue={revenue}")
        
        # 기존 데이터 확인 (stock_code, dart_code, bsns_year 모두 일치해야 함)
        existing = db.query(FinancialStatement).filter(
            FinancialStatement.stock_code == stock_code,
            FinancialStatement.dart_code == dart_code,
            FinancialStatement.bsns_year == bsns_year
        ).first()
        
        if existing:
            # 업데이트 - 새로운 딕셔너리 객체로 교체
            existing.financial_data = financial_data_final
            print(f"🔄 업데이트: 기존 레코드 ID={existing.id}")
        else:
            # 새로 생성 - 완전히 새로운 딕셔너리 객체 사용
            new_stmt = FinancialStatement(
                stock_code=stock_code,
                dart_code=dart_code,
                bsns_year=bsns_year,
                financial_data=financial_data_final
            )
            db.add(new_stmt)
            print(f"➕ 새로 생성: stock_code={stock_code}, dart_code={dart_code}")
        
        db.commit()
        
        # commit 후 객체를 expire하여 세션에서 분리 (참조 공유 방지)
        if existing:
            db.expire(existing)
        else:
            db.expire(new_stmt)
        
        # 저장 후 검증: 실제로 저장된 데이터 확인
        saved = db.query(FinancialStatement).filter(
            FinancialStatement.stock_code == stock_code,
            FinancialStatement.dart_code == dart_code,
            FinancialStatement.bsns_year == bsns_year
        ).first()
        
        if saved and saved.financial_data:
            saved_revenue = saved.financial_data.get("revenue", 0)
            print(f"✅ 저장 완료: ID={saved.id}, 저장된 revenue={saved_revenue}")
        
        return True
    except Exception as e:
        print(f"⚠️  DB 저장 실패 ({stock_code}, {dart_code}, {bsns_year}): {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False


def get_financial_statements_by_year(
    dart_code: str,
    bsns_year: str
) -> Optional[Dict]:
    """
    특정 연도의 재무제표를 DART API로 조회하고 파싱합니다.
    
    Args:
        dart_code: DART 기업코드 (8자리)
        bsns_year: 사업연도 (YYYY 형식)
    
    Returns:
        파싱된 재무 데이터 딕셔너리 또는 None
    """
    if not dart_code:
        return None
    
    # API 호출 제한을 고려하여 짧은 대기
    time.sleep(0.1)
    
    dart_data = get_financial_statements(dart_code, bsns_year)
    
    if not dart_data:
        return None
    
    financial_data = parse_financial_data(dart_data)
    
    # 데이터가 비어있으면 None 반환
    if not financial_data:
        return None
    
    # 추가 계산 지표
    if financial_data.get("revenue") and financial_data.get("operating_profit"):
        financial_data["operating_margin"] = (financial_data["operating_profit"] / financial_data["revenue"]) * 100
    
    if financial_data.get("total_assets") and financial_data.get("total_debt"):
        financial_data["debt_ratio"] = (financial_data["total_debt"] / financial_data["total_assets"]) * 100
    
    if financial_data.get("current_assets") and financial_data.get("current_liabilities"):
        financial_data["current_ratio"] = financial_data["current_assets"] / financial_data["current_liabilities"] if financial_data["current_liabilities"] > 0 else 0
    
    if financial_data.get("equity") and financial_data.get("total_assets"):
        financial_data["equity_ratio"] = (financial_data["equity"] / financial_data["total_assets"]) * 100
    
    # 딕셔너리를 deep copy하여 반환 (참조 공유 방지)
    return copy.deepcopy(financial_data)


def download_corpcode_xml() -> Optional[bytes]:
    """
    DART API에서 corpCode.xml 파일을 다운로드합니다.
    
    Returns:
        XML 파일의 바이트 데이터 또는 None (실패 시)
    """
    if not DART_API_KEY:
        print("⚠️  DART_API_KEY 환경 변수가 설정되지 않았습니다.")
        return None
    
    url = f"{DART_API_BASE_URL}/corpCode.xml"
    
    params = {
        "crtfc_key": DART_API_KEY
    }
    
    try:
        print("📥 corpCode.xml 파일 다운로드 중...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # ZIP 파일로 압축되어 있으므로 압축 해제
        zip_file = zipfile.ZipFile(BytesIO(response.content))
        xml_file = zip_file.open("CORPCODE.xml")
        xml_content = xml_file.read()
        xml_file.close()
        zip_file.close()
        
        print(f"✅ corpCode.xml 다운로드 완료 ({len(xml_content)} bytes)")
        return xml_content
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️  corpCode.xml 다운로드 실패: {e}")
        return None
    except zipfile.BadZipFile as e:
        print(f"⚠️  ZIP 파일 파싱 실패: {e}")
        return None
    except Exception as e:
        print(f"⚠️  corpCode.xml 처리 실패: {e}")
        return None


def load_stock_to_dart_mapping() -> Dict[str, str]:
    """
    corpCode.xml 파일을 파싱하여 stock_code -> dart_code 매핑 테이블을 생성합니다.
    매핑 테이블은 모듈 레벨에서 캐싱됩니다.
    
    Returns:
        stock_code -> dart_code 매핑 딕셔너리
    """
    global _stock_to_dart_mapping
    
    # 이미 로드된 경우 캐시 반환
    if _stock_to_dart_mapping is not None:
        return _stock_to_dart_mapping
    
    print("📊 stock_code -> dart_code 매핑 테이블 생성 중...")
    
    # XML 파일 다운로드
    xml_content = download_corpcode_xml()
    if not xml_content:
        print("⚠️  매핑 테이블 생성 실패: XML 파일을 다운로드할 수 없습니다.")
        _stock_to_dart_mapping = {}
        return _stock_to_dart_mapping
    
    # XML 파싱
    mapping = {}
    try:
        root = ET.fromstring(xml_content)
        
        for corp in root.findall("list"):
            corp_code = corp.find("corp_code")
            stock_code = corp.find("stock_code")
            
            if corp_code is not None and stock_code is not None:
                corp_code_text = corp_code.text.strip() if corp_code.text else ""
                stock_code_text = stock_code.text.strip() if stock_code.text else ""
                
                # stock_code가 비어있지 않고 6자리 숫자인 경우만 추가
                if stock_code_text and len(stock_code_text) == 6 and stock_code_text.isdigit():
                    if len(corp_code_text) == 8:  # dart_code는 8자리
                        mapping[stock_code_text] = corp_code_text
        
        _stock_to_dart_mapping = mapping
        print(f"✅ 매핑 테이블 생성 완료: {len(mapping)}개 회사")
        
    except ET.ParseError as e:
        print(f"⚠️  XML 파싱 실패: {e}")
        _stock_to_dart_mapping = {}
    except Exception as e:
        print(f"⚠️  매핑 테이블 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        _stock_to_dart_mapping = {}
    
    return _stock_to_dart_mapping


def get_dart_code_from_stock_code(stock_code: str) -> Optional[str]:
    """
    stock_code로부터 dart_code를 조회합니다.
    
    Args:
        stock_code: 종목코드 (6자리)
    
    Returns:
        DART 기업코드 (8자리) 또는 None (조회 실패 시)
    """
    if not stock_code or len(stock_code) != 6 or not stock_code.isdigit():
        return None
    
    # 매핑 테이블 로드
    mapping = load_stock_to_dart_mapping()
    
    # 조회
    dart_code = mapping.get(stock_code)
    
    if dart_code:
        return dart_code
    else:
        print(f"⚠️  stock_code {stock_code}에 대한 dart_code를 찾을 수 없습니다.")
        return None
