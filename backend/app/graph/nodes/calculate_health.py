"""
Health Factor 계산 노드
재무 데이터를 기반으로 각 회사의 health_factor를 계산합니다.
"""
from typing import Dict, Any
import sys
import os

# models 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.graph.state import ReportGenerationState


def calculate_health_factor(state: ReportGenerationState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    재무 데이터를 기반으로 각 회사의 health_factor를 계산합니다.
    
    계산 요소:
    - 매출 성장률 (가중치: 0.3)
    - 수익성 (영업이익률, 가중치: 0.3)
    - 안정성 (부채비율, 유동비율, 가중치: 0.2)
    - 수익성 추세 (최근 성장률, 가중치: 0.2)
    
    Args:
        state: 현재 상태
        
    Returns:
        업데이트된 상태
    """
    financial_data = state.get("financial_data", {})
    companies_by_industry = state.get("companies_by_industry", {})
    
    if not financial_data:
        print("⚠️  재무 데이터가 없습니다.")
        return {
            "health_factors": {},
            "errors": state.get("errors", []) + ["재무 데이터가 없습니다."]
        }
    
    health_factors = {}
    
    # 모든 회사 수집
    all_companies = []
    for industry_name, companies in companies_by_industry.items():
        for company in companies:
            stock_code = company.get("stock_code")
            if stock_code:
                all_companies.append({
                    "stock_code": stock_code,
                    "stock_name": company.get("stock_name", "알 수 없음"),
                    "industry": industry_name
                })
    
    print(f"💊 Health Factor 계산 시작: {len(all_companies)}개 회사")
    
    for company in all_companies:
        stock_code = company.get("stock_code")
        stock_name = company.get("stock_name")
        financials = financial_data.get(stock_code, {})
        
        if not financials:
            # 재무 데이터가 없으면 기본값
            health_factors[stock_code] = {
                "health_factor": 0.5,
                "calculation_details": {
                    "revenue_growth_score": 0.5,
                    "profitability_score": 0.5,
                    "stability_score": 0.5,
                    "trend_score": 0.5
                },
                "note": "재무 데이터 없음"
            }
            continue
        
        # 1. 매출 성장률 점수 (0-1) - 선형 변환: -10% ~ 20% 범위를 0.0 ~ 1.0으로
        revenue_growth = financials.get("revenue_growth", 0)
        # -10% 이하면 0.0, 20% 이상이면 1.0, 그 사이는 선형 보간
        revenue_growth_score = max(0.0, min(1.0, (revenue_growth + 10) / 30.0))
        
        # 2. 수익성 점수 (영업이익률, 0-1) - 선형 변환: 0% ~ 15% 범위를 0.0 ~ 1.0으로
        operating_margin = financials.get("operating_margin", 0)
        # 음수면 0.0, 15% 이상이면 1.0, 그 사이는 선형 보간
        profitability_score = max(0.0, min(1.0, operating_margin / 15.0))
        
        # 3. 안정성 점수 (부채비율, 유동비율, 0-1)
        debt_ratio = financials.get("debt_ratio", 100)
        current_ratio = financials.get("current_ratio", 0)
        
        # 부채비율 점수 (낮을수록 좋음) - 선형 변환: 30% 이하면 1.0, 100% 이상이면 0.0
        # 30% ~ 100% 범위를 1.0 ~ 0.0으로 선형 변환
        debt_score = max(0.0, min(1.0, (100 - debt_ratio) / 70.0))
        
        # 유동비율 점수 (높을수록 좋음) - 선형 변환: 0 ~ 2.0 범위를 0.0 ~ 1.0으로
        # 2.0 이상이면 1.0, 그 사이는 선형 보간
        current_score = max(0.0, min(1.0, current_ratio / 2.0))
        
        stability_score = (debt_score * 0.6 + current_score * 0.4)
        
        # 4. 수익성 추세 점수 (영업이익 성장률, 0-1) - 선형 변환: -10% ~ 20% 범위를 0.0 ~ 1.0으로
        operating_profit_growth = financials.get("operating_profit_growth", 0)
        # -10% 이하면 0.0, 20% 이상이면 1.0, 그 사이는 선형 보간
        trend_score = max(0.0, min(1.0, (operating_profit_growth + 10) / 30.0))
        
        # 최종 health_factor 계산 (가중 평균)
        health_factor = (
            revenue_growth_score * 0.3 +
            profitability_score * 0.3 +
            stability_score * 0.2 +
            trend_score * 0.2
        )
        
        # 0-1 범위로 제한
        health_factor = max(0.0, min(1.0, health_factor))
        
        health_factors[stock_code] = {
            "health_factor": health_factor,
            "calculation_details": {
                "revenue_growth_score": revenue_growth_score,
                "profitability_score": profitability_score,
                "stability_score": stability_score,
                "trend_score": trend_score
            }
        }
        
        print(f"✅ {stock_name} ({stock_code}): Health Factor = {health_factor:.2f}")
    
    print(f"✅ Health Factor 계산 완료: {len(health_factors)}개 회사")
    
    return {
        "health_factors": health_factors,
        "errors": state.get("errors", [])
    }
