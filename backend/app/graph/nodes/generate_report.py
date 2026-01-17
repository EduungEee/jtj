"""
보고서 생성 노드
모든 정보를 종합하여 최종 보고서 데이터를 생성합니다.
"""
from typing import Dict, Any, List
import sys
import os
import json
import re

# models 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.graph.state import ReportGenerationState
from app.analysis import get_openai_client


def generate_report(state: ReportGenerationState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    모든 정보를 종합하여 최종 보고서 데이터를 생성합니다.
    
    Args:
        state: 현재 상태
        
    Returns:
        업데이트된 상태
    """
    selected_news = state.get("selected_news", [])
    selection_reasons = state.get("selection_reasons", {})
    predicted_industries = state.get("predicted_industries", [])
    companies_by_industry = state.get("companies_by_industry", {})
    health_factors = state.get("health_factors", {})
    
    if not selected_news or not predicted_industries:
        return {
            "report_data": {},
            "errors": state.get("errors", []) + ["보고서 생성에 필요한 데이터가 부족합니다."]
        }
    
    client = get_openai_client()
    if not client:
        return {
            "report_data": {},
            "errors": state.get("errors", []) + ["OpenAI 클라이언트를 사용할 수 없습니다."]
        }
    
    try:
        # 뉴스 요약 생성
        news_items = []
        for article in selected_news:
            content_preview = article.content[:300] if article.content else "내용 없음"
            reason = selection_reasons.get(article.id, "선별됨")
            news_items.append(f"- {article.title} (선별 이유: {reason})")
        
        news_summary = "\n".join(news_items)
        
        # 산업군 정보 요약 (related_news_ids 포함)
        industry_summary = []
        industry_news_map = {}  # 산업별 뉴스 정보 저장
        for industry in predicted_industries:
            industry_name = industry.get("industry_name", "")
            selection_reason = industry.get("selection_reason", "")
            companies = companies_by_industry.get(industry_name, [])
            related_news_ids = industry.get("related_news_ids", [])
            
            # 산업별 관련 뉴스 정보 수집
            related_news_info = []
            for news_id in related_news_ids:
                news = next((n for n in selected_news if n.id == news_id), None)
                if news:
                    content_preview = news.content[:200] if news.content else "내용 없음"
                    related_news_info.append(f"  - [ID: {news_id}] {news.title}\n    내용: {content_preview}")
            
            industry_news_map[industry_name] = related_news_info
            news_list_text = "\n".join(related_news_info) if related_news_info else "  (관련 뉴스 없음)"
            industry_summary.append(f"- {industry_name}: {len(companies)}개 회사, {len(related_news_ids)}개 관련 뉴스, 선별 이유: {selection_reason}\n{news_list_text}")
        
        industry_text = "\n".join(industry_summary)
        
        prompt = f"""다음 정보를 바탕으로 주식 투자 보고서를 작성해주세요.

선별된 뉴스:
{news_summary}

예측된 산업군:
{industry_text}

다음 JSON 형식으로 응답해주세요:
{{
  "summary": "전체 뉴스 요약 및 주식 동향 분석 근거 (500-800자). <p> 태그로 문단을 분리해주세요. 예: <p>첫 번째 문단</p><p>두 번째 문단</p>",
  "industries": [
    {{
      "industry_name": "산업명",
      "impact_level": "high|medium|low",
      "impact_description": "영향 설명",
      "trend_direction": "positive|negative|neutral",
      "selection_reason": "산업 선별 이유",
      "news_impacts": [
        {{
          "news_id": int,
          "impact_on_industry": "이 뉴스가 해당 산업에 미치는 영향 설명 (100-200자)"
        }}
      ],
      "companies": [
        {{
          "stock_code": "종목코드",
          "stock_name": "종목명",
          "dart_code": "DART 코드",
          "health_factor": float,
          "reasoning": "회사 선정 이유"
        }}
      ]
    }}
  ]
}}

주의사항:
- summary는 반드시 <p> 태그로 문단을 분리해주세요
- summary는 500-800자 범위로 작성해주세요
- 각 산업의 news_impacts는 위에 나열된 관련 뉴스 ID들에 대해서만 작성해주세요
- news_id는 반드시 위에 나열된 뉴스 ID와 일치해야 합니다
- 각 회사의 health_factor는 제공된 값을 사용해주세요"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 주식 투자 보고서 작성 전문가입니다. 명확하고 구조화된 보고서를 작성합니다."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # 실제 데이터로 보강
        report_data = {
            "summary": result.get("summary", ""),
            "industries": []
        }
        
        # 산업군별로 실제 데이터 병합
        for industry_data in result.get("industries", []):
            industry_name = industry_data.get("industry_name", "")
            
            # 실제 산업 데이터 찾기
            actual_industry = None
            for ind in predicted_industries:
                if ind.get("industry_name") == industry_name:
                    actual_industry = ind
                    break
            
            if not actual_industry:
                continue
            
            # 관련 뉴스 데이터 보강 (related_news_ids를 기반으로 직접 구성)
            related_news = []
            related_news_ids = actual_industry.get("related_news_ids", [])
            
            # LLM이 생성한 news_impacts에서 impact_on_industry 매핑 생성
            news_impacts_map = {}
            for news_impact in industry_data.get("news_impacts", []):
                news_id = news_impact.get("news_id")
                if news_id:
                    news_impacts_map[news_id] = news_impact.get("impact_on_industry", "")
            
            # related_news_ids를 기반으로 실제 뉴스 데이터로 구성
            for news_id in related_news_ids:
                news = next((n for n in selected_news if n.id == news_id), None)
                if news:
                    # LLM이 생성한 impact_on_industry 가져오기 (없으면 기본값)
                    impact_desc = news_impacts_map.get(news_id, f"{news.title}이(가) {industry_name} 산업에 영향을 미칩니다.")
                    
                    related_news.append({
                        "news_id": news.id,
                        "title": news.title,
                        "url": news.url or "",
                        "published_at": news.published_at.strftime("%Y-%m-%d %H:%M:%S") if news.published_at else "",
                        "impact_on_industry": impact_desc
                    })
            
            # 회사 데이터 보강
            companies = []
            industry_companies = companies_by_industry.get(industry_name, [])
            
            for company_data in industry_data.get("companies", []):
                stock_code = company_data.get("stock_code", "")
                
                # 실제 회사 데이터 찾기
                actual_company = next(
                    (c for c in industry_companies if c.get("stock_code") == stock_code),
                    None
                )
                
                if actual_company:
                    health_data = health_factors.get(stock_code, {})
                    health_factor = health_data.get("health_factor", 0.5)
                    
                    companies.append({
                        "stock_code": stock_code,
                        "stock_name": company_data.get("stock_name", actual_company.get("stock_name", "")),
                        "dart_code": company_data.get("dart_code", actual_company.get("dart_code", "")),
                        "health_factor": health_factor,
                        "reasoning": company_data.get("reasoning", actual_company.get("reasoning", ""))
                    })
            
            report_data["industries"].append({
                "industry_name": industry_name,
                "impact_level": industry_data.get("impact_level", actual_industry.get("impact_level", "medium")),
                "impact_description": industry_data.get("impact_description", actual_industry.get("impact_description", "")),
                "trend_direction": industry_data.get("trend_direction", actual_industry.get("trend_direction", "neutral")),
                "selection_reason": industry_data.get("selection_reason", actual_industry.get("selection_reason", "")),
                "related_news": related_news,
                "companies": companies
            })
        
        print(f"✅ 보고서 생성 완료: {len(report_data['industries'])}개 산업, {len(selected_news)}개 뉴스")
        
        return {
            "report_data": report_data,
            "errors": state.get("errors", [])
        }
        
    except json.JSONDecodeError as e:
        error_msg = f"보고서 생성 결과 파싱 실패: {str(e)}"
        print(f"⚠️  {error_msg}")
        return {
            "report_data": {},
            "errors": state.get("errors", []) + [error_msg]
        }
    except Exception as e:
        import traceback
        error_msg = f"보고서 생성 실패: {str(e)}"
        print(f"⚠️  {error_msg}")
        print(traceback.format_exc())
        return {
            "report_data": {},
            "errors": state.get("errors", []) + [error_msg]
        }
