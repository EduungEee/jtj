"""
LangGraph pipeline skeleton (multi-stage industry/stock analysis).
Prompts are intentionally omitted; user will add them.
"""
import json
import os
from typing import List, Dict, Optional, TypedDict
from langgraph.graph import StateGraph, END


# ==================== State ====================

class PipelineState(TypedDict):
    # Input
    news_content: str
    corp_code_map: Optional[Dict[str, str]]

    # Node 1 outputs
    primary_industry: Optional[str]
    primary_reasoning: Optional[str]
    primary_stocks: List[Dict[str, str]]  # [{"code": "...", "name": "..."}]

    # Validation (Node 2)
    primary_industry_valid: bool
    primary_stocks_valid: bool
    primary_validation_msg: str

    # Exclusions for Node 1
    excluded_industries: List[str]
    excluded_stocks: List[str]

    # Financial data (Node 4 input)
    financial_statements: Optional[str]

    # Node 4 outputs (secondary perspective)
    secondary_industry: Optional[str]
    secondary_reasoning: Optional[str]
    secondary_stocks: List[Dict[str, str]]

    # Validation (Node 5)
    secondary_industry_valid: bool
    secondary_stocks_valid: bool
    secondary_validation_msg: str

    # Exclusions for Node 4
    excluded_secondary_industries: List[str]
    excluded_secondary_stocks: List[str]

    # Report (Node 7)
    report_summary: Optional[str]
    report_payload: Optional[Dict]

    # Loop control
    max_retries: int
    primary_retry_count: int
    secondary_retry_count: int


# ==================== Nodes ====================

def build_financial_statements_from_dart(
    stocks: List[Dict[str, str]],
    corp_code_map: Optional[Dict[str, str]],
    bsns_year: str = "2023",
    reprt_code: str = "11011",
) -> Optional[str]:
    if not stocks or not corp_code_map:
        return None

    from app.stock_api.dart_api import get_financial_statements

    corp_codes: List[str] = []
    code_to_name: Dict[str, str] = {}
    for stock in stocks:
        stock_code = stock.get("code")
        stock_name = stock.get("name") or stock_code
        corp_code = corp_code_map.get(stock_code) if stock_code else None
        if corp_code:
            corp_codes.append(corp_code)
            code_to_name[corp_code] = stock_name

    if not corp_codes:
        return None

    result = get_financial_statements(corp_codes, bsns_year=bsns_year, reprt_code=reprt_code)
    if not result.get("success"):
        return None

    items = result.get("data", [])
    if not items:
        return None

    target_accounts = ("자기자본비율", "부채비율", "유동비율")
    grouped: Dict[str, List[Dict]] = {code: [] for code in corp_codes}
    for item in items:
        corp_code = item.get("corp_code")
        account_nm = item.get("account_nm", "")
        if corp_code in grouped and any(key in account_nm for key in target_accounts):
            grouped[corp_code].append(item)

    lines: List[str] = []
    for corp_code in corp_codes:
        name = code_to_name.get(corp_code, corp_code)
        lines.append(f"[{name} 재무제표]")
        entries = grouped.get(corp_code) or []
        if not entries:
            lines.append(" - 핵심 지표 데이터 없음")
            continue
        for entry in entries:
            account_nm = entry.get("account_nm", "항목")
            amount = entry.get("thstrm_amount", "N/A")
            currency = entry.get("currency", "")
            lines.append(f" - {account_nm}: {amount} {currency}".strip())

    return "\n".join(lines)

def node_primary_recommendation(state: PipelineState) -> Dict:
    """
    Node 1: Analyze news -> derive industry + primary stocks.
    Prompts to be added by user.
    """
    prediction_output = {
        "news_content": state.get("news_content", ""),
    }

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
""".strip()

    prompt = f"""
[원본_뉴스]
{state.get("news_content", "")}
[원본_뉴스_끝]
"""

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("⚠️ GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다. 기본값으로 진행합니다.")
        return {
            "primary_industry": "",
            "primary_reasoning": "",
            "primary_stocks": [],
            "primary_retry_count": state.get("primary_retry_count", 0) + 1,
        }

    try:
        import google.generativeai as genai
    except ImportError:
        print("⚠️ google-generativeai 패키지가 설치되지 않았습니다.")
        return {
            "primary_industry": "",
            "primary_reasoning": "",
            "primary_stocks": [],
            "primary_retry_count": state.get("primary_retry_count", 0) + 1,
        }

    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    full_prompt = f"{system_prompt}\n\n{prompt}"
    response = model.generate_content(
        full_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.0
        ),
    )
    raw_text = response.text if hasattr(response, "text") else str(response)

    def extract_json(text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return ""
        return text[start : end + 1]

    payload: Dict = {}
    extracted = extract_json(raw_text)
    if extracted:
        try:
            payload = json.loads(extracted)
        except json.JSONDecodeError:
            payload = {}

    industries = payload.get("industries", []) if isinstance(payload, dict) else []
    primary_industry = ""
    primary_reasoning = ""
    primary_stocks: List[Dict[str, str]] = []

    if industries:
        first = industries[0] or {}
        impact_desc = (first.get("impact_description") or {}) if isinstance(first, dict) else {}
        buy_candidates = impact_desc.get("buy_candidates", []) if isinstance(impact_desc, dict) else []
        if buy_candidates:
            candidate = buy_candidates[0] or {}
            primary_industry = candidate.get("industry", "")
            primary_reasoning = candidate.get("reason_industry", "")
            stocks = candidate.get("stocks", []) if isinstance(candidate, dict) else []
            for stock in stocks:
                if not isinstance(stock, dict):
                    continue
                code = stock.get("stock_code") or stock.get("code") or ""
                name = stock.get("stock_name") or stock.get("name") or ""
                if code or name:
                    primary_stocks.append({"code": code, "name": name})

    return {
        "primary_industry": primary_industry,
        "primary_reasoning": primary_reasoning,
        "primary_stocks": primary_stocks,
        "primary_retry_count": state.get("primary_retry_count", 0) + 1,
    }


def node_primary_validation(state: PipelineState) -> Dict:
    """
    Node 2: Validate primary industry relevance and stock financial health.
    Prompts to be added by user.
    """
    prediction_output = {
        "industry": state.get("primary_industry", ""),
        "stocks": state.get("primary_stocks", []),
        "reasoning": state.get("primary_reasoning", ""),
    }
    original_news = state.get("news_content", "")
    financial_data = state.get("financial_statements", "")
    if not financial_data:
        financial_data = build_financial_statements_from_dart(
            stocks=state.get("primary_stocks", []),
            corp_code_map=state.get("corp_code_map"),
        ) or ""

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
유동비율 = 유동자산 / 유동부채
부채비율 = 부채총계 / 자본총계
자기자본비율 = 자본총계 / 자산총계
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
""".strip()

    prompt = f"""
[예측_LLM_출력]
{prediction_output}
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

    # TODO: system_prompt + prompt로 LLM 호출 결과를 파싱해 아래 값에 반영
    return {
        "primary_industry_valid": True,
        "primary_stocks_valid": True,
        "primary_validation_msg": "",
    }


def node_secondary_recommendation(state: PipelineState) -> Dict:
    """
    Node 4: Using financials + Node1 reasoning, propose affected stocks
    from different perspective.
    - Option A: same industry, different reasoning
    - Option B: different industry
    Prompts to be added by user.
    """
    prediction_json = {
        "primary_industry": state.get("primary_industry"),
        "primary_reasoning": state.get("primary_reasoning"),
        "primary_stocks": state.get("primary_stocks", []),
    }
    news_data = state.get("news_content", "")

    system_prompt = """
당신은 예측 LLM의 2차·3차 종목 추천을 재평가하는 **대안적 공급망 분석 전문가**다.

## 역할: 관점 전환 분석
1. **예측 LLM reasoning 관점**을 정확히 파악 (공급망 상 → 하류)
2. **3가지 대안적 관점**에서 완전히 다른 2차·3차 종목 추천:
   - 경쟁사 관점 (Competitor Logic)
   - 대체재/보완재 관점 (Substitution/Complement Logic)
   - 역방향 공급망 관점 (Upstream Reversal)

## 대안 관점별 추천 규칙

### 관점 1: 경쟁사 관점 (Market Share Shift)
예측 LLM: [1차 종목] 공급업체 추천
대안: [1차 종목]의 직접 경쟁사 공급업체
예: 삼성전자(1차) → SK하이닉스 공급업체(예측)
대안: SK하이닉스 공급업체(삼성 경쟁사 공급업체)

### 관점 2: 대체재/보완재 관점 (Substitution/Complement)
예측 LLM: HBM 메모리 공급업체(2차)
대안1: DDR5/LPDDR5 등 대체 메모리 공급업체
대안2: AI 서버 CPU/스토리지 등 보완 부품 공급업체

### 관점 3: 역방향 공급망 (Upstream Reversal)
예측 LLM: 반도체 제조 → 후공정 장비(3차)
대안: 후공정 장비의 원자재/부품 공급업체
(장비 제조사의 공급망으로 역추적)

## 입력 데이터 형식
[예측_LLM_출력]
{예측_JSON}
[예측_LLM_출력_끝]

[원본_뉴스]
{news_data}
[원본_뉴스_끝]
""".strip()

    user_prompt = f"""
위 예측 LLM이 추천한 2차·3차 종목들의 **reasoning 관점을 정확히 분석**하라.

## 분석 단계 1: 예측 LLM 관점 파악
예측 LLM의 각 2차·3차 종목별 reasoning에서:
1. 1차 종목 → 2차 연결고리 (공급/고객/파트너)
2. 2차 → 3차 연결고리 (다음 단계 공급망)
3. 사용된 논리 (수요 전이/생산 확대/투자 증가 등)

## 분석 단계 2: 3가지 대안 관점에서 재추천

### [관점 1] 경쟁사 관점
예측: [1차 종목A] → [2차 공급업체B]
대안: [1차 종목A의 경쟁사C] → [공급업체B의 경쟁사D]

### [관점 2] 대체재/보완재 관점
예측: HBM 메모리 공급업체
대안1: DDR5 등 대체 메모리 공급업체
대안2: AI 서버용 SSD/CPU 공급업체

### [관점 3] 역방향 공급망
예측: 반도체 생산 → 후공정 장비
대안: 후공정 장비 → 장비용 원자재/부품 공급업체

## 출력 형식 (유효 JSON만)
{{
  "alternative_analysis": {{
    "original_logic_summary": "예측 LLM의 핵심 논리 요약",
    "alternative_perspectives": [
      {{
        "perspective": "경쟁사_관점",
        "original_2nd_3rd": ["예측2차종목", "예측3차종목"],
        "alternative_stocks": [
          {{
            "stock_code": "대안종목코드",
            "stock_name": "대안종목명",
            "new_logic": "1차[원종목] 경쟁사[경쟁사명]의 핵심 공급업체",
            "confidence_score": 0.6,
            "impact_chain_level": 2
          }}
        ]
      }},
      {{
        "perspective": "대체재_보완재",
        "original_2nd_3rd": ["예측2차종목", "예측3차종목"],
        "alternative_stocks": [...]
      }},
      {{
        "perspective": "역방향_공급망",
        "original_2nd_3rd": ["예측2차종목", "예측3차종목"],
        "alternative_stocks": [...]
      }}
    ]
  }},

  "recommendation_comparison": {{
    "diversification_benefit": "대안 종목들이 포트폴리오 다각화에 기여하는 정도",
    "risk_reduction": "원래 추천 대비 리스크 분산 효과",
    "action_suggestion": "대안 일부 채택/전체 교체/관찰"
  }}
}}

## 제한사항
- 1차 종목은 절대 변경하지 말라 (예측 LLM 그대로 유지)
- 각 관점당 최소 1개, 최대 3개 대안 종목
- confidence_score는 원래 LLM 기준 유지 (1차0.7↑, 2차0.5↑, 3차0.3↑)
- **reasoning 관점 완전 전환**: 예측 LLM과 동일한 논리 금지
"""

    # TODO: system_prompt + user_prompt로 LLM 호출 후 결과 파싱
    # NOTE: 이후 conditional edge에서 합당성 판단을 위해
    # secondary_industry_valid / secondary_stocks_valid 값 설정 필요.
    return {
        "secondary_industry": "",
        "secondary_reasoning": "",
        "secondary_stocks": [],
        "secondary_retry_count": state.get("secondary_retry_count", 0) + 1,
    }


def node_secondary_validation(state: PipelineState) -> Dict:
    """
    Node 5: Validate secondary industry relevance and stock financial health.
    Prompts to be added by user.
    """
    prediction_output = {
        "industry": state.get("secondary_industry", ""),
        "stocks": state.get("secondary_stocks", []),
        "reasoning": state.get("secondary_reasoning", ""),
    }
    original_news = state.get("news_content", "")
    financial_data = state.get("financial_statements", "")

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
유동비율 = 유동자산 / 유동부채
부채비율 = 부채총계 / 자본총계
자기자본비율 = 자본총계 / 자산총계
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
""".strip()

    prompt = f"""
[예측_LLM_출력]
{prediction_output}
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

    # TODO: system_prompt + prompt로 LLM 호출 결과를 파싱해 아래 값에 반영
    return {
        "secondary_industry_valid": True,
        "secondary_stocks_valid": True,
        "secondary_validation_msg": "",
    }


def node_report_builder(state: PipelineState) -> Dict:
    """
    Node 7: Build report payload for UI sidebar (industry + short reasoning).
    """
    # TODO: implement
    return {
        "report_summary": "",
        "report_payload": {
            "primary_industry": state.get("primary_industry"),
            "primary_reasoning": state.get("primary_reasoning"),
            "secondary_industry": state.get("secondary_industry"),
            "secondary_reasoning": state.get("secondary_reasoning"),
        },
    }


# ==================== Routers ====================

def route_after_primary_validation(state: PipelineState) -> str:
    """
    Primary validation routing:
    - Valid (industry + stocks) -> Node 4
    - Invalid -> back to Node 1
    """
    if state.get("primary_industry_valid", False) and state.get("primary_stocks_valid", False):
        return "valid"
    return "invalid"


def route_after_secondary_validation(state: PipelineState) -> str:
    """
    If invalid -> retry secondary recommendation.
    If valid -> proceed to report.
    """
    if not state.get("secondary_industry_valid", False):
        return "retry"
    if not state.get("secondary_stocks_valid", False):
        return "retry"
    return "report"


# ==================== Workflow ====================

def build_pipeline():
    graph = StateGraph(PipelineState)

    graph.add_node("primary_recommendation", node_primary_recommendation)
    graph.add_node("primary_validation", node_primary_validation)
    graph.add_node("secondary_recommendation", node_secondary_recommendation)
    graph.add_node("secondary_validation", node_secondary_validation)
    graph.add_node("report", node_report_builder)

    graph.set_entry_point("primary_recommendation")
    graph.add_edge("primary_recommendation", "primary_validation")

    graph.add_conditional_edges(
        "primary_validation",
        route_after_primary_validation,
        {
            "valid": "secondary_recommendation",
            "invalid": "primary_recommendation",
        },
    )

    graph.add_edge("secondary_recommendation", "secondary_validation")

    graph.add_conditional_edges(
        "secondary_validation",
        route_after_secondary_validation,
        {
            "retry": "secondary_recommendation",
            "report": "report",
        },
    )

    graph.add_edge("report", END)

    return graph.compile()

