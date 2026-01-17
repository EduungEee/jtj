"""
산업군 예측 노드
선별된 뉴스를 분석하여 유망한 산업군을 예측합니다.
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


def predict_industries(state: ReportGenerationState, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    선별된 뉴스를 분석하여 유망한 산업군을 예측합니다.
    
    Args:
        state: 현재 상태
        
    Returns:
        업데이트된 상태
    """
    selected_news = state.get("selected_news", [])
    news_scores = state.get("news_scores", {})
    
    if not selected_news:
        print("⚠️  선별된 뉴스가 없습니다.")
        return {
            "predicted_industries": [],
            "errors": state.get("errors", []) + ["선별된 뉴스가 없습니다."]
        }
    
    client = get_openai_client()
    if not client:
        return {
            "predicted_industries": [],
            "errors": state.get("errors", []) + ["OpenAI 클라이언트를 사용할 수 없습니다."]
        }
    
    try:
        # 뉴스 요약 생성
        news_items = []
        available_news_ids = []
        for idx, article in enumerate(selected_news, 1):
            content_preview = article.content[:500] if article.content else "내용 없음"
            score = news_scores.get(article.id, 0.5)
            news_items.append(f"""뉴스 ID: {article.id}
제목: {article.title}
내용: {content_preview}
점수: {score:.2f}""")
            available_news_ids.append(article.id)
        
        news_summary = "\n\n---\n\n".join(news_items)
        available_ids_str = ", ".join(map(str, available_news_ids))
        
        prompt = f"""다음 뉴스 기사들을 분석하여 주식 시장에 영향을 미칠 유망한 산업군을 예측해주세요.

사용 가능한 뉴스 ID 목록: [{available_ids_str}]

뉴스 기사:
{news_summary}

다음 JSON 형식으로 응답해주세요:
{{
  "industries": [
    {{
      "industry_name": "산업명 (예: 반도체, 금융, 에너지, IT, 자동차 등)",
      "impact_level": "high|medium|low",
      "impact_description": "해당 산업에 미치는 영향에 대한 상세 설명",
      "trend_direction": "positive|negative|neutral",
      "selection_reason": "이 산업을 선별한 구체적인 이유 (뉴스 내용을 바탕으로)",
      "related_news_ids": [정수, 정수, ...]  // 반드시 위에 나열된 "뉴스 ID" 값을 정수 배열로 제공
    }}
  ]
}}

중요한 주의사항:
- 한국 주식 시장에 집중하여 분석해주세요
- related_news_ids는 반드시 위에 나열된 "뉴스 ID" 값을 정수 배열로 제공해야 합니다
- 예를 들어, 뉴스 ID가 123, 456, 789라면 related_news_ids는 [123, 456] 또는 [789] 같은 형식이어야 합니다
- 각 산업군은 최소 1개 이상의 관련 뉴스 ID를 포함해야 합니다. related_news_ids가 비어있거나 null이면 안 됩니다
- selection_reason은 구체적이고 명확하게 작성해주세요
- 3-7개 정도의 산업군을 추천해주세요
- related_news_ids 필드는 필수입니다. 반드시 포함해주세요"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 주식 시장 분석 전문가입니다. 뉴스를 분석하여 유망한 산업군을 정확하게 예측합니다."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        predicted_industries = result.get("industries", [])
        
        # 관련 뉴스 ID 검증 (실제로 존재하는 뉴스 ID인지 확인)
        valid_news_ids = {news.id for news in selected_news}
        for industry in predicted_industries:
            related_ids = industry.get("related_news_ids", [])
            
            # 디버깅: 원본 related_news_ids 로깅
            if not related_ids:
                print(f"⚠️  산업 '{industry.get('industry_name')}'에 related_news_ids가 없습니다. LLM 응답: {industry}")
            elif not isinstance(related_ids, list):
                print(f"⚠️  산업 '{industry.get('industry_name')}'의 related_news_ids가 리스트가 아닙니다. 타입: {type(related_ids)}, 값: {related_ids}")
            
            # 유효한 뉴스 ID만 유지
            if isinstance(related_ids, list):
                industry["related_news_ids"] = [news_id for news_id in related_ids if news_id in valid_news_ids]
            else:
                industry["related_news_ids"] = []
            
            # 관련 뉴스가 없으면 제거하지 않고 경고만
            if not industry["related_news_ids"]:
                print(f"⚠️  산업 '{industry.get('industry_name')}'에 관련 뉴스가 없습니다. (원본: {related_ids}, 유효한 ID: {valid_news_ids})")
        
        print(f"✅ 산업군 예측 완료: {len(predicted_industries)}개 산업 예측")
        for industry in predicted_industries:
            print(f"   - {industry.get('industry_name')}: {len(industry.get('related_news_ids', []))}개 관련 뉴스")
        
        return {
            "predicted_industries": predicted_industries,
            "errors": state.get("errors", [])
        }
        
    except json.JSONDecodeError as e:
        error_msg = f"산업군 예측 결과 파싱 실패: {str(e)}"
        print(f"⚠️  {error_msg}")
        return {
            "predicted_industries": [],
            "errors": state.get("errors", []) + [error_msg]
        }
    except Exception as e:
        import traceback
        error_msg = f"산업군 예측 실패: {str(e)}"
        print(f"⚠️  {error_msg}")
        print(traceback.format_exc())
        return {
            "predicted_industries": [],
            "errors": state.get("errors", []) + [error_msg]
        }
