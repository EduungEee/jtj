"""
통합 AI 분석 모듈
OpenAI API (추론 + 검증) 통일 전략
"""
import os
from typing import List, Dict, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
import sys

# 기존 모델 import
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from models.models import NewsArticle, Report, ReportIndustry, ReportStock

# ==================== LLM 설정 ====================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI GPT-4 - 추론용 (빠른 모델)
llm_inference = ChatOpenAI(
    model="gpt-4o-mini",  # 빠르고 저렴한 추론용
    temperature=0.5,  # 창의적 추론을 위해 약간 높게
    api_key=OPENAI_API_KEY
)

# OpenAI GPT-4 - 검증용 (정확하고 엄격)
llm_validation = ChatOpenAI(
    model="gpt-4o-mini",  # 또는 "gpt-4o" (더 정확하지만 비싸)
    temperature=0.1,  # 검증은 일관성이 중요하므로 낮게
    api_key=OPENAI_API_KEY
)

print(f"✅ LLM 초기화 완료")
print(f"   - 추론 엔진: OpenAI GPT-4o-mini")
print(f"   - 검증 엔진: OpenAI GPT-4o-mini")

# ==================== Pydantic Models ====================

class StockInfo(BaseModel):
    """1차 수혜주 정보"""
    code: str = Field(description="종목코드 6자리", pattern=r"^\d{6}$")
    name: str = Field(description="종목명")
    reason: str = Field(description="수혜 이유")
    confidence_score: float = Field(default=50.0, ge=0, le=100)
    expected_trend: str = Field(default="up", pattern="^(up|down|neutral)$")

class SideEffectInfo(BaseModel):
    """2차 파급효과 정보"""
    sector: str = Field(description="파급 섹터 (= 산업명)")
    logic: str = Field(description="파급 논리")
    impact_level: str = Field(default="medium", pattern="^(high|medium|low)$")
    trend_direction: str = Field(default="positive", pattern="^(positive|negative|neutral)$")
    related_stocks: List[StockInfo] = Field(default_factory=list)

class NewsAnalysisOutput(BaseModel):
    """뉴스 분석 결과"""
    summary: str = Field(max_length=500)
    sentiment_score: float = Field(ge=-1, le=1)
    sentiment_label: str
    key_keywords: List[str]
    issue_category: str

class PrimaryOutput(BaseModel):
    """1차 수혜주 출력"""
    stocks: List[StockInfo]

class SideEffectOutput(BaseModel):
    """2차 파급효과 출력"""
    effects: List[SideEffectInfo]

class ValidationResult(BaseModel):
    """검증 결과"""
    is_valid: bool
    feedback: str
    confidence: float = Field(0.5, ge=0, le=1)
    issues: List[str] = Field(default_factory=list, description="발견된 문제점 리스트")

# ==================== Graph State ====================

from typing import TypedDict

class AnalysisState(TypedDict):
    # 입력
    news_articles: List[NewsArticle]
    max_primary_stocks: int
    max_side_effects: int
    max_retry: int
    
    # 분석 결과
    analysis: str
    sentiment_score: float
    sentiment_label: str
    key_keywords: List[str]
    issue_category: str
    
    # 1차 수혜주
    primary_stocks: List[Dict]
    primary_feedback: str
    primary_retry_count: int
    is_primary_valid: bool
    
    # 기술적 검증 (차트)
    technical_rejected: List[Dict]  # 차트 과열로 탈락한 종목들
    
    # 2차 파급효과
    side_effects: List[Dict]
    side_effect_feedback: str
    side_effect_retry_count: int
    is_side_effect_valid: bool
    
    # 메타데이터
    start_time: datetime
    llm_call_count: int
    openai_calls: int
    warnings: List[str]

# ==================== LangGraph Nodes ====================

def analyze_news_node(state: AnalysisState):
    """[1] 뉴스 분석 (OpenAI GPT 사용)"""
    print("--- [1] 뉴스 분석 시작 (OpenAI GPT) ---")
    
    news_articles = state["news_articles"]
    
    # 뉴스 요약 (최대 10개)
    news_summary = "\n\n".join([
        f"[{i+1}] 제목: {article.title}\n출처: {article.source}\n내용: {article.content[:300] if article.content else '내용 없음'}"
        for i, article in enumerate(news_articles[:10])
    ])
    
    prompt = f"""당신은 한국 주식시장 전문 애널리스트입니다.

[뉴스 기사들]
{news_summary}

[분석 요구사항]
1. 전체 뉴스의 핵심 이슈를 200자 이내로 요약
2. 시장 감성 점수 (-1.0=매우부정 ~ 1.0=매우긍정)
3. 감성 라벨 (매우긍정/긍정/중립/부정/매우부정)
4. 핵심 키워드 5개 추출 (주식 투자 관련)
5. 이슈 카테고리 분류 (정책/실적/기술/금리/지정학/기타)

JSON 형식으로 응답:
{{
    "summary": "요약",
    "sentiment_score": 0.0,
    "sentiment_label": "중립",
    "key_keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
    "issue_category": "정책"
}}
"""
    
    structured_llm = llm_inference.with_structured_output(NewsAnalysisOutput)
    result = structured_llm.invoke(prompt)
    
    print(f"✅ 분석 완료: {result.issue_category} 이슈, 감성={result.sentiment_label} (OpenAI)")
    
    return {
        "analysis": result.summary,
        "sentiment_score": result.sentiment_score,
        "sentiment_label": result.sentiment_label,
        "key_keywords": result.key_keywords,
        "issue_category": result.issue_category,
        "primary_retry_count": 0,
        "side_effect_retry_count": 0,
        "is_primary_valid": False,
        "is_side_effect_valid": False,
        "start_time": datetime.now(),
        "llm_call_count": 1,
        "openai_calls": 1,
        "warnings": []
    }

def primary_inference_node(state: AnalysisState):
    """[2] 1차 수혜주 추론 (OpenAI GPT 사용)"""
    retry_num = state.get("primary_retry_count", 0)
    print(f"--- [2] 1차 수혜주 추론 (시도 {retry_num + 1}회) (OpenAI GPT) ---")
    
    analysis = state["analysis"]
    feedback = state.get("primary_feedback", "")
    max_stocks = state.get("max_primary_stocks", 3)
    
    prompt = f"""당신은 한국 주식시장 전문가입니다.

[시장 분석]
{analysis}

[미션]
위 이슈로 가장 직접적인 수혜를 입을 한국 상장 종목을 {max_stocks}개 추천하세요.

[필수 조건]
1. 실제 존재하는 한국 종목 (코스피/코스닥)
2. 종목코드 6자리 필수 (예: 005930=삼성전자, 000660=SK하이닉스)
3. 확신도 점수 (0~100)
4. 예상 추세 (up/down/neutral)
5. 구체적인 수혜 이유

[예시]
- 반도체 호황 → 삼성전자(005930), SK하이닉스(000660)
- 전기차 보급 → LG에너지솔루션(373220), 삼성SDI(006400)
"""
    
    if feedback:
        prompt += f"\n\n[이전 시도에서 받은 검증관의 지적 (OpenAI GPT-4)]\n{feedback}\n\n⚠️ 위 지적사항을 반드시 반영하여 수정하세요!"
    
    structured_llm = llm_inference.with_structured_output(PrimaryOutput)
    result = structured_llm.invoke(prompt)
    
    print(f"✅ 추론 완료: {len(result.stocks)}개 종목 (OpenAI)")
    for stock in result.stocks:
        print(f"   - {stock.name}({stock.code}): {stock.confidence_score:.0f}점")
    
    return {
        "primary_stocks": [s.dict() for s in result.stocks],
        "llm_call_count": state["llm_call_count"] + 1,
        "openai_calls": state["openai_calls"] + 1
    }

def primary_validation_node(state: AnalysisState):
    """[3] 1차 수혜주 검증 (OpenAI GPT-4 사용)"""
    retry_num = state["primary_retry_count"]
    print(f"--- [3] 1차 수혜주 논리 검증 (시도 {retry_num + 1}회) (OpenAI GPT-4) ---")
    
    stocks = state["primary_stocks"]
    analysis = state["analysis"]
    
    prompt = f"""당신은 매우 엄격한 주식 분석 검증관입니다. OpenAI GPT가 추론한 종목을 검증하는 것이 임무입니다.

[원본 뉴스 분석]
{analysis}

[OpenAI GPT가 추론한 종목]
{stocks}

[검증 체크리스트]
✅ 1. 종목코드 실존성
   - 6자리 숫자 형식인가?
   - 실제 한국 상장 종목인가? (코스피/코스닥)
   - 예: 005930(삼성전자), 000660(SK하이닉스), 035720(카카오)

✅ 2. 논리 타당성
   - 뉴스 이슈와 종목의 연결이 직관적이고 명확한가?
   - "A이기 때문에 B가 수혜받는다"의 논리가 성립하는가?

✅ 3. 과장 여부
   - 지나치게 비약적이거나 억지스러운 연결은 아닌가?
   - 실제 시장에서 받아들여질 만한 논리인가?

✅ 4. 직접성
   - 1차 직접 수혜주인가? (2차, 3차 파급효과는 나중 단계)
   - 이슈와 즉각적으로 관련이 있는가?

[판정 기준]
- 위 4가지 중 하나라도 문제 있으면: is_valid = False
- 모두 통과하면: is_valid = True, feedback = "검증 통과. 논리적으로 타당함."

문제가 있다면 구체적으로 어떤 종목의 어떤 부분이 문제인지 명시하세요.
"""
    
    structured_llm = llm_validation.with_structured_output(ValidationResult)
    result = structured_llm.invoke(prompt)
    
    status = "✅ 통과" if result.is_valid else "❌ 재시도 필요"
    print(f"{status} (OpenAI): {result.feedback[:100]}...")
    
    if result.issues:
        print(f"   발견된 문제점:")
        for issue in result.issues:
            print(f"   - {issue}")
    
    warnings = []
    if result.confidence < 0.7:
        warnings.append(f"1차 수혜주 신뢰도 낮음 ({result.confidence:.2f})")
    
    return {
        "primary_feedback": result.feedback,
        "primary_retry_count": state["primary_retry_count"] + 1,
        "is_primary_valid": result.is_valid,
        "llm_call_count": state["llm_call_count"] + 1,
        "openai_calls": state["openai_calls"] + 1,
        "warnings": state["warnings"] + warnings
    }

def technical_validation_node(state: AnalysisState):
    """
    [4] 기술적 지표 검증 (차트 분석)
    추천된 종목의 차트를 분석하여 '선반영(이미 오름)' 여부를 판단합니다.
    """
    print("--- [4] 📈 기술적 지표 분석 중 (차트 검증) ---")
    
    stocks = state["primary_stocks"]
    validated_stocks = []
    rejected_stocks = []
    
    import pandas as pd
    import numpy as np
    
    for stock in stocks:
        code = stock['code']
        name = stock['name']
        
        print(f"  분석 중: {name}({code})")
        
        # 1. 차트 데이터 가져오기
        df = get_daily_price(code, days=100)
        
        if df is None or len(df) < 30:
            print(f"    ⚠️ 차트 데이터 부족 - 스킵 (그대로 통과)")
            stock['technical_status'] = "데이터 부족"
            stock['technical_comment'] = "차트 데이터 조회 실패 (기본 통과)"
            validated_stocks.append(stock)
            continue
        
        try:
            # === 지표 계산 ===
            
            # A. RSI (14일)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # B. 이격도 (20일): (현재가 / 20일이동평균) * 100
            ma_20 = df['Close'].rolling(window=20).mean()
            disparity = (df['Close'] / ma_20) * 100
            current_disparity = disparity.iloc[-1]
            
            # C. 볼린저 밴드 (20일, 승수 2)
            std_dev = df['Close'].rolling(window=20).std()
            upper_band = ma_20 + (std_dev * 2)
            lower_band = ma_20 - (std_dev * 2)
            current_price = df['Close'].iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            current_ma = ma_20.iloc[-1]
            
            # === 냉정한 판정 (Logic) ===
            
            is_priced_in = False  # 선반영 되었는가?
            reasons = []
            score = 0  # 과열 점수 (0-3점)
            
            # 조건 1: RSI가 70 이상이면 과열
            if current_rsi >= 70:
                is_priced_in = True
                reasons.append(f"RSI 과열({current_rsi:.1f})")
                score += 1
            
            # 조건 2: 이격도가 110% 이상이면 단기 급등 상태
            if current_disparity >= 110:
                is_priced_in = True
                reasons.append(f"이격도 과다({current_disparity:.1f}%)")
                score += 1
            
            # 조건 3: 현재가가 볼린저밴드 상단을 뚫었으면 고점 징후
            if current_price >= current_upper:
                is_priced_in = True
                reasons.append(f"볼린저 상단 돌파(${current_price:,.0f} ≥ ${current_upper:,.0f})")
                score += 1
            
            # === 결론 도출 ===
            if not is_priced_in:
                # 통과! (아직 살 만함)
                stock['technical_status'] = "양호"
                stock['technical_score'] = f"RSI:{current_rsi:.1f}/이격도:{current_disparity:.1f}%"
                
                if current_rsi < 30 or current_price < current_lower:
                    stock['technical_comment'] = "✅ 차트 바닥권. 상승 여력 매우 높음"
                elif current_rsi < 50 and current_disparity < 105:
                    stock['technical_comment'] = "✅ 차트 상승 초기. 매수 적기"
                else:
                    stock['technical_comment'] = "✅ 차트 정상 범위. 매수 유효"
                
                validated_stocks.append(stock)
                print(f"    ✅ 통과: {stock['technical_comment']}")
                
            else:
                # 탈락! (이미 다 올랐음)
                if score >= 2:
                    # 2개 이상 과열 신호 → 완전 탈락
                    stock['technical_status'] = "과열"
                    stock['technical_comment'] = f"❌ {', '.join(reasons)} - 선반영됨"
                    rejected_stocks.append(stock)
                    print(f"    ❌ 탈락: {stock['technical_comment']}")
                else:
                    # 1개만 과열 → 경고와 함께 통과
                    stock['technical_status'] = "주의"
                    stock['technical_comment'] = f"⚠️ {', '.join(reasons)} - 주의 필요"
                    validated_stocks.append(stock)
                    print(f"    ⚠️ 조건부 통과: {stock['technical_comment']}")
                    
        except Exception as e:
            print(f"    ⚠️ 지표 계산 오류: {e} - 기본 통과")
            stock['technical_status'] = "계산 오류"
            stock['technical_comment'] = f"지표 계산 실패 (기본 통과)"
            validated_stocks.append(stock)
    
    # 결과 요약
    print(f"\n  📊 기술적 검증 결과:")
    print(f"    ✅ 통과: {len(validated_stocks)}개")
    print(f"    ❌ 탈락: {len(rejected_stocks)}개")
    
    if rejected_stocks:
        print(f"    탈락 종목: {', '.join([s['name'] for s in rejected_stocks])}")
    
    warnings = []
    if len(validated_stocks) == 0:
        warnings.append("⚠️ 모든 종목이 기술적으로 과열 - 추천 불가")
    elif len(rejected_stocks) > 0:
        warnings.append(f"{len(rejected_stocks)}개 종목이 차트 과열로 제외됨")
    
    return {
        "primary_stocks": validated_stocks,
        "technical_rejected": rejected_stocks,
        "warnings": state["warnings"] + warnings
    }

def side_effect_inference_node(state: AnalysisState):
    """[5] 2차 파급효과 추론 (OpenAI GPT 사용)"""
    retry_num = state.get("side_effect_retry_count", 0)
    print(f"--- [5] 2차 파급효과 추론 (시도 {retry_num + 1}회) (OpenAI GPT) ---")
    
    analysis = state["analysis"]
    primary_stocks = state["primary_stocks"]
    feedback = state.get("side_effect_feedback", "")
    max_effects = state.get("max_side_effects", 2)
    
    prompt = f"""당신은 산업 연관관계 분석 전문가입니다. 창의적이고 통찰력 있는 2차 파급효과를 찾아내세요.

[시장 이슈]
{analysis}

[1차 직접 수혜주]
{primary_stocks}

[미션]
1차 수혜주가 상승하거나 이슈가 지속될 때, 연쇄적으로 수혜를 받을 산업과 종목을 최대 {max_effects}개 추론하세요.

[파급 체인 예시]
1️⃣ 전기차 판매 증가
   → 배터리 수요 증가 (1차: 삼성SDI, LG에너지솔루션)
   → 배터리 소재 수요 증가 (2차: 포스코케미칼, 에코프로비엠)
   → 폐배터리 재활용 필요 (2차: 성일하이텍, 파워로직스)

2️⃣ 반도체 투자 확대
   → 반도체 장비 수요 (1차: 주성엔지니어링, 원익IPS)
   → 반도체 소재 수요 (2차: 솔브레인, SK머티리얼즈)
   → 정밀 부품 수요 (2차: 테스, 코세스)

3️⃣ K-콘텐츠 수출 증가
   → 엔터테인먼트 기업 (1차: HYBE, SM, JYP)
   → 플랫폼/유통사 (2차: 넷마블, 카카오엔터)
   → 제작사/스튜디오 (2차: 스튜디오드래곤, 에이스토리)

[출력 형식]
각 산업별로:
- sector: 산업명 (명확하고 구체적으로)
- logic: A → B → C 형태의 파급 논리
- impact_level: high/medium/low
- trend_direction: positive/negative/neutral
- related_stocks: 관련 종목 리스트 (종목코드 6자리 + 종목명)
"""
    
    if feedback:
        prompt += f"\n\n[이전 시도에서 받은 검증관의 지적 (OpenAI GPT-4)]\n{feedback}\n\n⚠️ 논리를 더 구체화하고 실현 가능한 시나리오로 수정하세요!"
    
    structured_llm = llm_inference.with_structured_output(SideEffectOutput)
    result = structured_llm.invoke(prompt)
    
    print(f"✅ 추론 완료: {len(result.effects)}개 산업 (OpenAI)")
    for effect in result.effects:
        print(f"   - {effect.sector} ({effect.impact_level}): {len(effect.related_stocks)}개 종목")
    
    return {
        "side_effects": [e.dict() for e in result.effects],
        "llm_call_count": state["llm_call_count"] + 1,
        "openai_calls": state["openai_calls"] + 1
    }

def side_effect_validation_node(state: AnalysisState):
    """[6] 파급효과 검증 (OpenAI GPT-4 사용)"""
    retry_num = state["side_effect_retry_count"]
    print(f"--- [6] 파급효과 검증 (시도 {retry_num + 1}회) (OpenAI GPT-4) ---")
    
    effects = state["side_effects"]
    primary_stocks = state["primary_stocks"]
    
    prompt = f"""당신은 논리적 인과관계 검증 전문가입니다. OpenAI GPT가 추론한 파급효과를 검증하는 것이 임무입니다.

[1차 수혜주]
{primary_stocks}

[OpenAI GPT가 추론한 2차 파급효과]
{effects}

[검증 체크리스트]
✅ 1. 인과관계 명확성
   - A → B → C의 연결고리가 논리적으로 타당한가?
   - 각 단계의 인과관계가 실제로 성립하는가?

✅ 2. 실현 가능성
   - 실제로 발생할 수 있는 시나리오인가?
   - 과거 사례나 시장 경험상 합리적인가?

✅ 3. 비약 여부
   - 너무 억지스럽거나 비현실적이지 않은가?
   - 1차 → 2차로의 점프가 자연스러운가?

✅ 4. 시장 합리성
   - 실제 투자자들이 이 논리를 받아들일 만한가?
   - 추천된 종목들이 실제로 존재하고 관련성이 있는가?

[판정 기준]
- 모든 기준 통과: is_valid = True
- 일부 문제: is_valid = False + 구체적 수정사항 명시

문제가 있다면 어떤 산업의 어떤 논리가 문제인지 구체적으로 지적하세요.
"""
    
    structured_llm = llm_validation.with_structured_output(ValidationResult)
    result = structured_llm.invoke(prompt)
    
    status = "✅ 통과" if result.is_valid else "❌ 재시도 필요"
    print(f"{status} (OpenAI): {result.feedback[:100]}...")
    
    if result.issues:
        print(f"   발견된 문제점:")
        for issue in result.issues:
            print(f"   - {issue}")
    
    warnings = []
    if result.confidence < 0.6:
        warnings.append(f"파급효과 신뢰도 낮음 ({result.confidence:.2f})")
    
    return {
        "side_effect_feedback": result.feedback,
        "side_effect_retry_count": state["side_effect_retry_count"] + 1,
        "is_side_effect_valid": result.is_valid,
        "llm_call_count": state["llm_call_count"] + 1,
        "openai_calls": state["openai_calls"] + 1,
        "warnings": state["warnings"] + warnings
    }

# ==================== Edge Conditions ====================

def check_primary(state: AnalysisState):
    """1차 검증 통과 여부"""
    is_valid = state.get("is_primary_valid", False)
    retry_count = state.get("primary_retry_count", 0)
    max_retry = state.get("max_retry", 3)
    
    if is_valid or retry_count >= max_retry:
        if retry_count >= max_retry and not is_valid:
            print(f"⚠️ 최대 시도 횟수 도달, 강제 통과 (OpenAI가 {max_retry}회 시도)")
        return "pass"
    return "retry"

def check_side_effect(state: AnalysisState):
    """2차 검증 통과 여부"""
    is_valid = state.get("is_side_effect_valid", False)
    retry_count = state.get("side_effect_retry_count", 0)
    max_retry = state.get("max_retry", 3)
    
    if is_valid or retry_count >= max_retry:
        if retry_count >= max_retry and not is_valid:
            print(f"⚠️ 최대 시도 횟수 도달, 강제 통과 (Gemini가 {max_retry}회 시도)")
        return "pass"
    return "retry"

# ==================== Graph Construction ====================

workflow = StateGraph(AnalysisState)

workflow.add_node("analyze_news", analyze_news_node)
workflow.add_node("primary_inference", primary_inference_node)
workflow.add_node("primary_validation", primary_validation_node)
workflow.add_node("technical_validation", technical_validation_node)  # 📈 새로 추가
workflow.add_node("side_effect_inference", side_effect_inference_node)
workflow.add_node("side_effect_validation", side_effect_validation_node)

workflow.set_entry_point("analyze_news")
workflow.add_edge("analyze_news", "primary_inference")
workflow.add_edge("primary_inference", "primary_validation")

workflow.add_conditional_edges(
    "primary_validation",
    check_primary,
    {"pass": "technical_validation", "retry": "primary_inference"}  # 논리 검증 통과 → 차트 검증
)

workflow.add_edge("technical_validation", "side_effect_inference")  # 차트 검증 → 파급효과

workflow.add_edge("side_effect_inference", "side_effect_validation")

workflow.add_conditional_edges(
    "side_effect_validation",
    check_side_effect,
    {"pass": END, "retry": "side_effect_inference"}
)

app = workflow.compile()

# ==================== DB Integration ====================

def save_to_database(
    db: Session,
    news_articles: List[NewsArticle],
    state: AnalysisState,
    analysis_date: date
) -> Report:
    """LangGraph 분석 결과를 기존 DB 스키마에 저장"""
    print("--- [7] 데이터베이스 저장 시작 ---")
    
    # Report 생성
    report = Report(
        title=f"{analysis_date.strftime('%Y-%m-%d')} 주식 동향 분석 (OpenAI AI)",
        summary=state["analysis"],
        analysis_date=analysis_date
    )
    db.add(report)
    db.flush()
    
    # 뉴스 연결
    for news in news_articles:
        report.news_articles.append(news)
    
    # 1차 수혜주를 첫 번째 산업으로 저장
    primary_industry = ReportIndustry(
        report_id=report.id,
        industry_name="1차 직접 수혜주",
        impact_level="high",
        impact_description=f"뉴스 이슈({state['issue_category']})로 인한 직접 수혜",
        trend_direction="positive" if state.get("sentiment_score", 0) > 0 else "neutral"
    )
    db.add(primary_industry)
    db.flush()
    
    # 1차 수혜주 저장
    for stock_data in state["primary_stocks"]:
        stock = ReportStock(
            report_id=report.id,
            industry_id=primary_industry.id,
            stock_code=stock_data["code"],
            stock_name=stock_data["name"],
            expected_trend=stock_data.get("expected_trend", "up"),
            confidence_score=stock_data.get("confidence_score", 50.0) / 100.0,
            reasoning=stock_data["reason"]
        )
        db.add(stock)
    
    # 2차 파급효과 (산업별로 저장)
    for effect_data in state["side_effects"]:
        industry = ReportIndustry(
            report_id=report.id,
            industry_name=effect_data["sector"],
            impact_level=effect_data.get("impact_level", "medium"),
            impact_description=effect_data["logic"],
            trend_direction=effect_data.get("trend_direction", "positive")
        )
        db.add(industry)
        db.flush()
        
        # 관련 종목 저장
        for stock_data in effect_data.get("related_stocks", []):
            stock = ReportStock(
                report_id=report.id,
                industry_id=industry.id,
                stock_code=stock_data["code"],
                stock_name=stock_data["name"],
                expected_trend=stock_data.get("expected_trend", "up"),
                confidence_score=stock_data.get("confidence_score", 50.0) / 100.0,
                reasoning=stock_data["reason"]
            )
            db.add(stock)
    
    db.commit()
    db.refresh(report)
    
    print(f"✅ 데이터베이스 저장 완료: Report ID={report.id}")
    return report

# ==================== Main API Function ====================

def analyze_news_with_langgraph(
    db: Session,
    news_articles: List[NewsArticle],
    max_primary_stocks: int = 3,
    max_side_effects: int = 2,
    max_retry: int = 3,
    analysis_date: Optional[date] = None
) -> Report:
    """
    뉴스를 OpenAI GPT로 분석하고 결과를 DB에 저장
    - 추론: OpenAI GPT-4o-mini (빠르고 저렴)
    - 검증: OpenAI GPT-4o-mini (정확하고 엄격)
    """
    if not news_articles:
        raise ValueError("분석할 뉴스 기사가 없습니다.")
    
    if analysis_date is None:
        analysis_date = date.today()
    
    print(f"==================== OpenAI AI 분석 시작 ====================")
    print(f"뉴스 개수: {len(news_articles)}")
    print(f"옵션: primary={max_primary_stocks}, side={max_side_effects}, retry={max_retry}")
    print(f"전략: 추론(OpenAI GPT) + 검증(OpenAI GPT)")
    print(f"=" * 60)
    
    # 초기 상태
    initial_state = {
        "news_articles": news_articles,
        "max_primary_stocks": max_primary_stocks,
        "max_side_effects": max_side_effects,
        "max_retry": max_retry
    }
    
    try:
        # LangGraph 실행
        result = app.invoke(initial_state)
        
        # 결과 출력
        end_time = datetime.now()
        processing_time = (end_time - result["start_time"]).total_seconds()
        
        print(f"\n{'=' * 60}")
        print(f"✅ 분석 완료")
        print(f"처리 시간: {processing_time:.2f}초")
        print(f"총 LLM 호출: {result['llm_call_count']}회")
        print(f"  └─ OpenAI GPT: {result['openai_calls']}회")
        print(f"총 반복 횟수: {result['primary_retry_count']}회 (1차) + {result['side_effect_retry_count']}회 (2차)")
        print(f"{'=' * 60}\n")
        
        # 3. 결과 DB 저장 및 반환
        report = save_to_database(db, news_articles, result, analysis_date)
        return report

    except Exception as e:
        import traceback
        print(f"\n❌ 분석 중 치명적 오류 발생: {e}")
        print(traceback.format_exc())
        raise 

# ==================== Backward Compatibility ====================

def analyze_and_save(
    db: Session,
    news_articles: List[NewsArticle],
    analysis_date: Optional[date] = None
) -> Report:
    """
    기존 API와의 호환성을 위한 래퍼 함수
    
    기존 코드에서 이 함수를 호출하면 자동으로 LangGraph 사용
    """
    return analyze_news_with_langgraph(
        db=db,
        news_articles=news_articles,
        analysis_date=analysis_date
    )


def analyze_news_from_vector_db(
    db: Session,
    start_datetime: Optional[datetime] = None,
    end_datetime: Optional[datetime] = None,
    analysis_date: Optional[date] = None
) -> Report:
    """
    벡터 DB에서 날짜 범위로 뉴스를 조회하고, AI 분석을 수행하여 보고서를 생성합니다.
    
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
    from datetime import timedelta
    import pytz
    
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
    
    if analysis_date is None:
        analysis_date = date.today()
    
    # 벡터 DB에서 뉴스 조회 (날짜 범위로)
    # metadata의 published_date를 기준으로 조회
    from sqlalchemy import text
    
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
            start_str = start_datetime.isoformat()
            end_str = end_datetime.isoformat()
            
            cursor.execute("""
                SELECT id FROM news_articles
                WHERE metadata IS NOT NULL
                AND metadata->>'published_date' IS NOT NULL
                AND (
                    (metadata->>'published_date')::timestamp >= %s::timestamp
                    AND (metadata->>'published_date')::timestamp <= %s::timestamp
                )
                ORDER BY (metadata->>'published_date')::timestamp DESC
                LIMIT 20
            """, (start_str, end_str))
            
            article_ids = [row[0] for row in cursor.fetchall()]
            news_articles = db.query(NewsArticle).filter(NewsArticle.id.in_(article_ids)).all() if article_ids else []
            
            print(f"✅ 벡터 DB에서 뉴스 조회 완료: {len(news_articles)}개 (기간: {start_datetime.strftime('%Y-%m-%d %H:%M')} ~ {end_datetime.strftime('%Y-%m-%d %H:%M')})")
        finally:
            cursor.close()
        
    except Exception as e:
        import traceback
        print(f"⚠️  벡터 DB 뉴스 조회 실패: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"벡터 DB에서 뉴스를 조회할 수 없습니다: {e}")
    
    if not news_articles:
        raise ValueError(f"조회된 뉴스 기사가 없습니다. (기간: {start_datetime} ~ {end_datetime})")
    
    # 분석 및 저장
    report = analyze_news_with_langgraph(
        db=db,
        news_articles=news_articles,
        analysis_date=analysis_date
    )
    
    print(f"✅ 벡터 DB 기반 분석 완료: 보고서 ID={report.id}, 뉴스 {len(news_articles)}개 분석")
    
    return report


# ==================== 한국투자증권 API 함수 ====================

KIS_APP_KEY = os.getenv("KIS_APP_KEY")
KIS_APP_SECRET = os.getenv("KIS_APP_SECRET")
KIS_ACCESS_TOKEN = None

def get_kis_access_token():
    """한국투자증권 API 토큰 발급"""
    global KIS_ACCESS_TOKEN
    
    if not KIS_APP_KEY or not KIS_APP_SECRET:
        print("⚠️ 한투 API 키 없음 - 기술적 검증 스킵")
        return None
    
    if KIS_ACCESS_TOKEN:
        return KIS_ACCESS_TOKEN
    
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET
    }
    
    try:
        import requests
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 200:
            KIS_ACCESS_TOKEN = response.json()["access_token"]
            print("✅ 한투 API 토큰 발급 성공")
            return KIS_ACCESS_TOKEN
    except Exception as e:
        print(f"⚠️ 한투 API 토큰 발급 실패: {e}")
    
    return None


def get_daily_price(stock_code: str, days: int = 100):
    """
    한국투자증권 API로 일봉 데이터 조회
    
    Args:
        stock_code: 종목코드 (6자리)
        days: 조회할 일수
    
    Returns:
        DataFrame with columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    """
    token = get_kis_access_token()
    if not token:
        return None
    
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-price"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
        "tr_id": "FHKST01010400"
    }
    
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
        "FID_PERIOD_DIV_CODE": "D",
        "FID_ORG_ADJ_PRC": "0"
    }
    
    try:
        import requests
        import pandas as pd
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"⚠️ {stock_code} 차트 조회 실패: {response.status_code}")
            return None
        
        data = response.json()
        if data.get("rt_cd") != "0":
            print(f"⚠️ {stock_code} 데이터 없음")
            return None
        
        output = data.get("output", [])
        if not output:
            return None
        
        # DataFrame 생성
        df = pd.DataFrame(output[:days])
        df = df.rename(columns={
            "stck_bsop_date": "Date",
            "stck_oprc": "Open",
            "stck_hgpr": "High",
            "stck_lwpr": "Low",
            "stck_clpr": "Close",
            "acml_vol": "Volume"
        })
        
        # 숫자 변환
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.sort_values("Date").reset_index(drop=True)
        
        return df[["Date", "Open", "High", "Low", "Close", "Volume"]]
        
    except Exception as e:
        print(f"⚠️ {stock_code} 차트 조회 오류: {e}")
        return None
