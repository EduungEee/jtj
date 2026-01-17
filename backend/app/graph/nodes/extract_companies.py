"""
산업별 회사 목록 추출 노드
각 산업군에 대해 관련 회사 목록을 추출합니다.
"""
from typing import Dict, Any, List
import sys
import os
import json

# models 경로 추가
backend_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.graph.state import ReportGenerationState
from app.analysis import get_openai_client
from app.services.dart_api import get_dart_code_from_stock_code


def extract_companies(state: ReportGenerationState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    각 산업군에 대해 관련 회사 목록을 추출합니다.
    
    Args:
        state: 현재 상태
        
    Returns:
        업데이트된 상태
    """
    predicted_industries = state.get("predicted_industries", [])
    selected_news = state.get("selected_news", [])
    
    if not predicted_industries:
        print("⚠️  예측된 산업군이 없습니다.")
        return {
            "companies_by_industry": {},
            "errors": state.get("errors", []) + ["예측된 산업군이 없습니다."]
        }
    
    client = get_openai_client()
    if not client:
        return {
            "companies_by_industry": {},
            "errors": state.get("errors", []) + ["OpenAI 클라이언트를 사용할 수 없습니다."]
        }
    
    try:
        # 뉴스에서 언급된 회사 정보 추출
        news_text = "\n".join([f"- {news.title}" for news in selected_news[:10]])  # 상위 10개만
        
        companies_by_industry = {}
        
        # 각 산업군별로 회사 추출
        for industry in predicted_industries:
            industry_name = industry.get("industry_name", "")
            related_news_ids = industry.get("related_news_ids", [])
            
            # 관련 뉴스 필터링
            related_news = [news for news in selected_news if news.id in related_news_ids]
            related_news_text = "\n".join([f"- {news.title}" for news in related_news])
            
            prompt = f"""다음 산업군과 관련 뉴스를 바탕으로 해당 산업에 속하는 한국 주식 시장의 주요 회사 목록을 추출해주세요.

산업군: {industry_name}

관련 뉴스:
{related_news_text}

다음 JSON 형식으로 응답해주세요:
{{
  "companies": [
    {{
      "stock_code": "종목코드 (6자리, 예: 005930)",
      "stock_name": "종목명 (예: 삼성전자)",
      "dart_code": "DART 코드 (8자리, 예: 00126380)",
      "reasoning": "이 회사를 추천하는 이유 (간단히)"
    }}
  ]
}}

주의사항:
- 실제 존재하는 한국 주식 시장의 상장 기업만 추천해주세요
- 각 산업군당 3-10개 정도의 회사를 추천해주세요
- 뉴스에서 언급된 회사가 있으면 우선적으로 포함해주세요
- stock_code는 반드시 6자리 숫자여야 합니다
- DART 코드(dart_code)는 정확한 8자리 숫자만 제공해주세요
- DART 코드를 정확히 모르거나 확신이 없으면 빈 문자열("")로 반환해주세요
- 추측하거나 임의의 값을 넣지 마세요 (예: 모든 회사에 같은 dart_code를 넣지 마세요)"""
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "당신은 한국 주식 시장 전문가입니다. 산업군별로 적절한 회사를 정확하게 추천합니다."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.5
                )
                
                result_text = response.choices[0].message.content
                result = json.loads(result_text)
                
                companies = result.get("companies", [])
                
                # 데이터 검증 및 정리
                validated_companies = []
                for company in companies:
                    stock_code = company.get("stock_code", "").strip()
                    stock_name = company.get("stock_name", "").strip()
                    dart_code = company.get("dart_code", "").strip()
                    reasoning = company.get("reasoning", "").strip()
                    
                    # stock_code가 6자리 숫자인지 확인
                    if stock_code and len(stock_code) == 6 and stock_code.isdigit():
                        # dart_code 검증 및 보정
                        # dart_code가 없거나 빈 문자열이거나 8자리가 아닌 경우 매핑 테이블에서 조회
                        if not dart_code or len(dart_code) != 8 or not dart_code.isdigit():
                            # 매핑 테이블에서 조회
                            resolved_dart_code = get_dart_code_from_stock_code(stock_code)
                            if resolved_dart_code:
                                # 매핑 테이블에서 찾은 경우 보정
                                dart_code = resolved_dart_code
                                print(f"✅ {stock_name} ({stock_code}): dart_code를 매핑 테이블에서 조회하여 보정 ({dart_code})")
                            else:
                                # 매핑 테이블에서도 찾을 수 없는 경우
                                print(f"⚠️  {stock_name} ({stock_code}): dart_code를 찾을 수 없습니다. 빈 문자열로 저장됩니다.")
                                dart_code = ""
                        else:
                            # LLM이 제공한 dart_code가 유효한 경우 그대로 사용
                            pass
                        
                        validated_companies.append({
                            "stock_code": stock_code,
                            "stock_name": stock_name,
                            "dart_code": dart_code,
                            "reasoning": reasoning
                        })
                    else:
                        print(f"⚠️  잘못된 종목코드 무시: {stock_code} (산업: {industry_name})")
                
                companies_by_industry[industry_name] = validated_companies
                print(f"✅ {industry_name}: {len(validated_companies)}개 회사 추출")
                
            except json.JSONDecodeError as e:
                print(f"⚠️  {industry_name} 회사 추출 결과 파싱 실패: {e}")
                companies_by_industry[industry_name] = []
            except Exception as e:
                print(f"⚠️  {industry_name} 회사 추출 실패: {e}")
                companies_by_industry[industry_name] = []
        
        total_companies = sum(len(companies) for companies in companies_by_industry.values())
        print(f"✅ 회사 목록 추출 완료: 총 {total_companies}개 회사")
        
        return {
            "companies_by_industry": companies_by_industry,
            "errors": state.get("errors", [])
        }
        
    except Exception as e:
        import traceback
        error_msg = f"회사 목록 추출 실패: {str(e)}"
        print(f"⚠️  {error_msg}")
        print(traceback.format_exc())
        return {
            "companies_by_industry": {},
            "errors": state.get("errors", []) + [error_msg]
        }
