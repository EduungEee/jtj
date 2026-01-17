"""
재무제표 조회 노드
DB에서 먼저 조회하고, 없으면 DART API를 통해 각 회사의 재무제표를 조회합니다.
1년 전부터 3년 전까지 순차적으로 조회합니다.
"""
from typing import Dict, Any, Optional
import sys
import os
import time
from datetime import datetime

# models 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.graph.state import ReportGenerationState
from app.services.dart_api import (
    get_financial_from_db,
    save_financial_to_db,
    get_financial_statements_by_year
)


def fetch_financial_data(state: ReportGenerationState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    DB에서 먼저 조회하고, 없으면 DART API를 통해 각 회사의 재무제표를 조회합니다.
    1년 전부터 3년 전까지 순차적으로 조회합니다.
    
    Args:
        state: 현재 상태
        config: 설정 (db 세션 포함)
        
    Returns:
        업데이트된 상태
    """
    companies_by_industry = state.get("companies_by_industry", {})
    
    if not companies_by_industry:
        print("⚠️  회사 목록이 없습니다.")
        return {
            "financial_data": {},
            "errors": state.get("errors", []) + ["회사 목록이 없습니다."]
        }
    
    # DB 세션 가져오기
    db = None
    if config and "db" in config:
        db = config["db"]
    
    financial_data = {}
    errors = state.get("errors", [])
    
    # 모든 회사 수집
    all_companies = []
    for industry_name, companies in companies_by_industry.items():
        for company in companies:
            all_companies.append({
                "industry": industry_name,
                "stock_code": company.get("stock_code"),
                "stock_name": company.get("stock_name"),
                "dart_code": company.get("dart_code")
            })
    
    print(f"📊 재무제표 조회 시작: {len(all_companies)}개 회사")
    
    # 현재 연도 기준으로 1년 전, 2년 전, 3년 전 계산
    current_year = datetime.now().year
    years_to_check = [
        str(current_year - 1),  # 1년 전
        str(current_year - 2),  # 2년 전
        str(current_year - 3)   # 3년 전
    ]
    
    # 각 회사의 재무제표 조회
    for idx, company in enumerate(all_companies, 1):
        stock_code = company.get("stock_code")
        dart_code = company.get("dart_code")
        stock_name = company.get("stock_name", "알 수 없음")
        
        if not dart_code:
            print(f"⚠️  [{idx}/{len(all_companies)}] {stock_name} ({stock_code}): DART 코드 없음, 스킵")
            continue
        
        if not stock_code:
            print(f"⚠️  [{idx}/{len(all_companies)}] {stock_name}: 종목코드 없음, 스킵")
            continue
        
        try:
            financials = None
            found_year = None
            
            # 1년 전부터 3년 전까지 순차적으로 조회
            for bsns_year in years_to_check:
                # 1. DB에서 먼저 조회
                if db:
                    financials = get_financial_from_db(db, stock_code, dart_code, bsns_year)
                    if financials:
                        print(f"📦 [{idx}/{len(all_companies)}] {stock_name} ({stock_code}): DB에서 {bsns_year}년 재무제표 조회 성공")
                        found_year = bsns_year
                        break
                
                # 2. DB에 없으면 DART API 호출
                if idx > 1:
                    time.sleep(0.2)  # API 호출 간격 (초당 5회 제한 고려)
                
                financials = get_financial_statements_by_year(dart_code, bsns_year)
                
                if financials:
                    print(f"🌐 [{idx}/{len(all_companies)}] {stock_name} ({stock_code}): DART API에서 {bsns_year}년 재무제표 조회 성공")
                    found_year = bsns_year
                    
                    # 3. DB에 저장
                    if db:
                        save_success = save_financial_to_db(db, stock_code, dart_code, bsns_year, financials)
                        if save_success:
                            print(f"💾 [{idx}/{len(all_companies)}] {stock_name} ({stock_code}): {bsns_year}년 재무제표 DB 저장 완료")
                    
                    break
            
            if financials:
                financial_data[stock_code] = financials
                print(f"✅ [{idx}/{len(all_companies)}] {stock_name} ({stock_code}): 재무제표 조회 성공 ({found_year}년)")
            else:
                print(f"⚠️  [{idx}/{len(all_companies)}] {stock_name} ({stock_code}): 재무제표 조회 실패 (1~3년 전 데이터 없음)")
                # 실패해도 계속 진행
                
        except Exception as e:
            error_msg = f"{stock_name} ({stock_code}) 재무제표 조회 중 오류: {str(e)}"
            print(f"⚠️  [{idx}/{len(all_companies)}] {error_msg}")
            errors.append(error_msg)
    
    success_count = len(financial_data)
    print(f"✅ 재무제표 조회 완료: {success_count}/{len(all_companies)}개 성공")
    
    return {
        "financial_data": financial_data,
        "errors": errors
    }
