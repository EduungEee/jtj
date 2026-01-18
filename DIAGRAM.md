# 📊 프로젝트 아키텍처 다이어그램

이 문서는 뉴스 기반 주식 동향 분석 서비스의 전체 구조와 동작 방식을 시각적으로 설명합니다.

## 🏗 시스템 아키텍처

```mermaid
graph TB
    subgraph "Client Layer"
        User[사용자]
        Browser[웹 브라우저]
    end

    subgraph "Frontend Layer"
        NextJS[Next.js 15<br/>App Router]
        Pages[페이지 컴포넌트]
        Components[UI 컴포넌트]
        APIClient[API 클라이언트]
    end

    subgraph "Backend Layer"
        FastAPI[FastAPI 서버<br/>:8000]
        Routers[API 라우터]
        Services[비즈니스 로직]
    end

    subgraph "External APIs"
        NewsDataAPI[NewsData.io API]
        NaverAPI[Naver News API]
        NewsOrgAPI[NewsAPI.org API]
        TheNewsAPI[The News API]
        OpenAIAPI[OpenAI API]
    end

    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL 15<br/>+ pgvector)]
        Adminer[Adminer<br/>:8080]
    end

    subgraph "Scheduler Layer"
        Scheduler[스케줄러<br/>APScheduler]
        NewsScheduler[뉴스 수집<br/>매시간]
        CleanupScheduler[뉴스 삭제<br/>매일 4시]
        AnalysisScheduler[일일 분석<br/>매일 6시]
        EmailScheduler[이메일 전송<br/>매일 7시]
    end

    subgraph "Email Services"
        EmailAPI[이메일 API<br/>SendGrid/Resend]
    end

    User --> Browser
    Browser --> NextJS
    NextJS --> Pages
    Pages --> Components
    Components --> APIClient
    APIClient -->|HTTP/REST| FastAPI
    FastAPI --> Routers
    Routers --> Services
    Services -->|뉴스 수집| NewsDataAPI
    Services -->|뉴스 수집| NaverAPI
    Services -->|뉴스 수집| NewsOrgAPI
    Services -->|뉴스 수집| TheNewsAPI
    Services -->|AI 분석| OpenAIAPI
    Services -->|데이터 저장/조회| PostgreSQL
    Adminer -->|관리| PostgreSQL
    Scheduler --> NewsScheduler
    Scheduler --> CleanupScheduler
    Scheduler --> AnalysisScheduler
    Scheduler --> EmailScheduler
    NewsScheduler -->|POST /api/get_news| FastAPI
    CleanupScheduler -->|DELETE /api/news/old| FastAPI
    AnalysisScheduler -->|POST /api/analyze| FastAPI
    EmailScheduler -->|POST /api/send-email| FastAPI
    Services -->|이메일 전송| EmailAPI
```

## 🔄 데이터 흐름도

### 1. 자동 뉴스 수집 플로우 (매시간)

```mermaid
sequenceDiagram
    participant Scheduler as 스케줄러
    participant Backend as FastAPI Backend
    participant NewsData as NewsData.io API
    participant DB as PostgreSQL (pgvector)

    Note over Scheduler: 매시간 자동 실행
    Scheduler->>Backend: POST /api/get_news 호출
    
    loop 각 뉴스 API Provider (Max Collection 전략)
        Backend->>ExternalAPI: 최신 뉴스 데이터 수집 요청 (변환된 쿼리 & Provider별 최대 수량)
        ExternalAPI-->>Backend: 뉴스 데이터 목록
        Note over Backend: 모든 Provider에서 최대 개수 수집
    end
    
    Backend->>Backend: 뉴스 데이터 통합 및 URL 기반 중복 제거
    Backend->>DB: 뉴스 기사 저장 (관계형 DB)
    Backend->>Backend: 벡터 임베딩 생성 (meta description 기반)
    Backend->>DB: 벡터 데이터 저장 (pgvector, metadata 포함)
```

### 2. 자동 일일 분석 플로우 (매일 아침 6시)

```mermaid
sequenceDiagram
    participant Scheduler as 스케줄러
    participant Backend as FastAPI Backend
    participant DB as PostgreSQL (pgvector)
    participant OpenAI as OpenAI API

    Note over Scheduler: 매일 아침 6시 자동 실행
    Scheduler->>Backend: POST /api/analyze 호출
    Backend->>DB: 벡터 DB에서 전날 6시~현재 뉴스 조회
    DB-->>Backend: 뉴스 기사 목록 (24시간치)
    Backend->>OpenAI: 뉴스 분석 요청 (취합된 뉴스)
    OpenAI-->>Backend: 분석 결과 (요약, 산업, 주식)

    Backend->>DB: 보고서 저장
    Backend->>DB: 산업 분석 저장
    Backend->>DB: 주식 분석 저장
```

### 3. 수동 분석 요청 플로우 (선택사항)

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Frontend as Next.js Frontend
    participant Backend as FastAPI Backend
    participant DB as PostgreSQL
    participant OpenAI as OpenAI API

    User->>Frontend: 분석 요청 (수동)
    Frontend->>Backend: POST /api/analyze
    Backend->>Backend: 날짜 검증 및 중복 확인

    alt 이미 분석된 날짜
        Backend-->>Frontend: 이미 존재하는 보고서 반환
    else 새로운 분석
        Backend->>DB: 벡터 DB에서 지정 기간 뉴스 조회
        DB-->>Backend: 뉴스 기사 목록
        Backend->>OpenAI: 뉴스 분석 요청
        OpenAI-->>Backend: 분석 결과 (요약, 산업, 주식)

        Backend->>DB: 보고서 저장
        Backend->>DB: 산업 분석 저장
        Backend->>DB: 주식 분석 저장

        Backend-->>Frontend: 보고서 ID 반환
        Frontend-->>User: 분석 완료 표시
    end
```

### 4. 이메일 전송 플로우 (매일 아침 7시)

```mermaid
sequenceDiagram
    participant Scheduler as 스케줄러
    participant Backend as FastAPI Backend
    participant DB as PostgreSQL
    participant EmailAPI as 이메일 API<br/>(SendGrid/Resend)

    Note over Scheduler: 매일 아침 7시 자동 실행
    Scheduler->>Backend: POST /api/send-email 호출
    Backend->>DB: 오늘 생성된 보고서 조회
    DB-->>Backend: 보고서 목록
    Backend->>DB: 구독자 이메일 목록 조회
    DB-->>Backend: 구독자 목록
    
    loop 각 구독자에게
        Backend->>EmailAPI: 보고서 링크 포함 이메일 전송
        EmailAPI-->>Backend: 전송 완료
    end
```

### 5. 보고서 조회 플로우

```mermaid
sequenceDiagram
    participant User as 사용자
    participant Frontend as Next.js Frontend
    participant Backend as FastAPI Backend
    participant DB as PostgreSQL

    User->>Frontend: 홈페이지 접속 (/)
    Frontend->>Backend: GET /api/reports/today
    Backend->>DB: 오늘 날짜 보고서 조회
    DB-->>Backend: 보고서 목록
    Backend-->>Frontend: 보고서 목록 JSON
    Frontend-->>User: 보고서 카드 표시

    User->>Frontend: 보고서 클릭
    Frontend->>Backend: GET /api/report/{id}
    Backend->>DB: 보고서 상세 조회 (관계 포함)
    DB-->>Backend: 보고서 + 뉴스 + 산업 + 주식
    Backend-->>Frontend: 보고서 상세 JSON
    Frontend-->>User: 상세 페이지 표시
```

## 📡 API 엔드포인트 구조

```mermaid
graph TB
    subgraph "FastAPI Server :8000"
        Health[GET /api/health]
        
        subgraph "뉴스 API"
            GetNews[POST /api/get_news<br/>뉴스 수집]
            NewsList[GET /api/news<br/>뉴스 조회]
            DeleteOld[DELETE /api/news/old<br/>뉴스 삭제]
        end
        
        subgraph "보고서 API"
            Analyze[POST /api/analyze<br/>보고서 작성]
            ReportsToday[GET /api/reports/today<br/>오늘의 보고서]
            ReportDetail[GET /api/report/:id<br/>보고서 상세]
        end
        
        subgraph "이메일 API"
            Subscribe[POST /api/subscribe<br/>이메일 구독]
            SendEmail[POST /api/send-email<br/>이메일 전송]
        end
    end

    GetNews -->|멀티 API Orchestration| ExternalAPIs[NewsData, Naver, NewsAPI.org, TheNewsAPI]
    GetNews -->|저장| DB1[(PostgreSQL<br/>+ pgvector)]
    NewsList -->|조회| DB1
    DeleteOld -->|삭제| DB1
    Analyze -->|벡터 DB 조회| DB1
    Analyze -->|분석| OpenAI[OpenAI API]
    Analyze -->|저장| DB2[(PostgreSQL)]
    ReportsToday -->|조회| DB2
    ReportDetail -->|조회| DB2
    SendEmail -->|전송| EmailAPI[이메일 API<br/>SendGrid/Resend]
```

## 🗄 데이터베이스 스키마

```mermaid
erDiagram
    REPORTS ||--o{ REPORT_NEWS : "has"
    NEWS_ARTICLES ||--o{ REPORT_NEWS : "belongs to"
    REPORTS ||--o{ REPORT_INDUSTRIES : "has"
    REPORT_INDUSTRIES ||--o{ REPORT_STOCKS : "has"

    REPORTS {
        int id PK
        string title
        text summary
        date analysis_date
        timestamp created_at
        jsonb report_metadata "report_data 저장용"
    }

    NEWS_ARTICLES {
        int id PK
        string title
        text content
        string source
        string url
        timestamp published_at
        timestamp collected_at
        string provider "뉴스 API 제공자"
        jsonb article_metadata "벡터 DB metadata"
        vector embedding "pgvector vector(1536)"
    }

    REPORT_NEWS {
        int report_id FK
        int news_id FK
    }

    REPORT_INDUSTRIES {
        int id PK
        int report_id FK
        string industry_name
        string impact_level "high, medium, low"
        text impact_description
        string trend_direction "positive, negative, neutral"
        text selection_reason "산업 선별 이유"
        timestamp created_at
    }

    REPORT_STOCKS {
        int id PK
        int report_id FK
        int industry_id FK
        string stock_code
        string stock_name
        string expected_trend "up, down, neutral"
        decimal confidence_score "0.00 ~ 1.00"
        text reasoning
        decimal health_factor "0.00 ~ 1.00"
        string dart_code "DART API용 코드"
        timestamp created_at
    }

    EMAIL_SUBSCRIPTIONS {
        int id PK
        string clerk_user_id UK "Clerk 사용자 ID"
        string email
        timestamp subscribed_at
        boolean is_active
    }

    FINANCIAL_STATEMENTS {
        int id PK
        string stock_code
        string dart_code
        string bsns_year "YYYY 형식"
        jsonb financial_data "재무 데이터"
        timestamp created_at
    }
```

## 🔧 기술 스택 상세

```mermaid
graph TB
    subgraph "Frontend"
        NextJS[Next.js 15]
        React[React 19]
        Tailwind[Tailwind CSS 4]
        TypeScript[TypeScript]
        Shadcn[shadcn/ui]
    end

    subgraph "Backend"
        FastAPI[FastAPI]
        SQLAlchemy[SQLAlchemy ORM]
        Pydantic[Pydantic]
        Python[Python 3.11+]
    end

    subgraph "Database"
        PostgreSQL[PostgreSQL 15<br/>+ pgvector]
        Adminer[Adminer]
    end

    subgraph "Scheduler"
        APScheduler[APScheduler]
    end

    subgraph "Email Services"
        SendGrid[SendGrid API]
        Resend[Resend API]
    end

    subgraph "External Services"
        NewsData[NewsData.io API]
        Naver[네이버 뉴스 API]
        NewsOrg[NewsAPI.org API]
        TheNewsAPI[The News API]
        OpenAI[OpenAI API]
    end

    subgraph "Infrastructure"
        Docker[Docker Compose]
        Network[Network Layer]
    end

    NextJS --> React
    NextJS --> Tailwind
    NextJS --> TypeScript
    NextJS --> Shadcn

    FastAPI --> SQLAlchemy
    FastAPI --> Pydantic
    FastAPI --> Python

    SQLAlchemy --> PostgreSQL
    Adminer --> PostgreSQL

    FastAPI --> APScheduler
    APScheduler --> NewsData
    APScheduler --> OpenAI
    FastAPI --> NewsData
    FastAPI --> OpenAI
    FastAPI --> SendGrid
    FastAPI --> Resend

    Docker --> NextJS
    Docker --> FastAPI
    Docker --> PostgreSQL
    Docker --> Adminer
```

## 🌐 네트워크 아키텍처

```mermaid
graph TB
    subgraph "Docker Network"
        subgraph "Frontend Container"
            NextJS[Next.js :3000]
        end

        subgraph "Backend Container"
            FastAPI[FastAPI :8000]
        end

        subgraph "Database Container"
            PostgreSQL[PostgreSQL :5432<br/>+ pgvector]
        end

        subgraph "Admin Container"
            Adminer[Adminer :8080]
        end
    end

    subgraph "External Services"
        NewsDataAPI[NewsData.io API<br/>newsdata.io]
        OpenAIAPI[OpenAI API<br/>api.openai.com]
        EmailAPI[이메일 API<br/>SendGrid/Resend]
    end

    NextJS <-->|HTTP/REST| FastAPI
    FastAPI <-->|SQL| PostgreSQL
    Adminer <-->|SQL| PostgreSQL
    FastAPI <-->|HTTPS| NewsDataAPI
    FastAPI <-->|HTTPS| OpenAIAPI
    FastAPI <-->|HTTPS| EmailAPI
```

## 🔄 LangGraph 보고서 생성 플로우

### Graph Node 전체 흐름

```mermaid
graph TB
    Start([분석 시작<br/>analysis_date, current_time]) --> FilterNews[filter_news_by_date<br/>날짜 범위 필터링]
    
    FilterNews -->|filtered_news| SelectNews[select_relevant_news<br/>뉴스 선별 및 점수화]
    
    SelectNews -->|selected_news<br/>news_scores<br/>selection_reasons| PredictIndustries[predict_industries<br/>산업군 예측]
    
    PredictIndustries -->|predicted_industries<br/>related_news_ids| ExtractCompanies[extract_companies<br/>회사 추출]
    
    ExtractCompanies -->|companies_by_industry<br/>stock_code, dart_code| FetchFinancials[fetch_financial_data<br/>재무 데이터 조회]
    
    FetchFinancials -->|financial_data| CalculateHealth[calculate_health_factor<br/>Health Factor 계산]
    
    CalculateHealth -->|health_factors| GenerateReport[generate_report<br/>보고서 생성]
    
    GenerateReport -->|report_data| End([완료])
    
    style FilterNews fill:#e1f5ff
    style SelectNews fill:#e1f5ff
    style PredictIndustries fill:#e1f5ff
    style ExtractCompanies fill:#e1f5ff
    style FetchFinancials fill:#e1f5ff
    style CalculateHealth fill:#e1f5ff
    style GenerateReport fill:#e1f5ff
```

### 각 노드의 상세 로직

#### 1. filter_news_by_date
```mermaid
flowchart TD
    Start([시작]) --> GetDate[analysis_date, current_time 가져오기]
    GetDate --> CalcRange[날짜 범위 계산<br/>전날 06:00 ~ 당일 23:59]
    CalcRange --> QueryDB[DB에서 뉴스 조회<br/>get_news_by_date_range]
    QueryDB --> Return[filtered_news 반환]
    Return --> End([종료])
```

#### 2. select_relevant_news
```mermaid
flowchart TD
    Start([시작]) --> GetNews[filtered_news 가져오기]
    GetNews --> CreateQuery[쿼리 임베딩 생성<br/>주식 영향도 높은 뉴스]
    CreateQuery --> SemanticSearch[Semantic Search<br/>벡터 유사도 검색]
    SemanticSearch --> LLMScore[LLM으로 점수화<br/>주식 영향도 평가]
    LLMScore --> SelectTop[상위 20개 선별]
    SelectTop --> Return[selected_news<br/>news_scores<br/>selection_reasons 반환]
    Return --> End([종료])
```

#### 3. predict_industries
```mermaid
flowchart TD
    Start([시작]) --> GetNews[selected_news 가져오기]
    GetNews --> LLMPredict[LLM으로 산업군 예측<br/>뉴스 분석하여 유망 산업 추출]
    LLMPredict --> MapNews[각 산업에 관련 뉴스 ID 매핑<br/>related_news_ids]
    MapNews --> Return[predicted_industries 반환<br/>industry_name, selection_reason, related_news_ids]
    Return --> End([종료])
```

#### 4. extract_companies
```mermaid
flowchart TD
    Start([시작]) --> GetIndustries[predicted_industries 가져오기]
    GetIndustries --> LoopIndustry{각 산업별 반복}
    LoopIndustry --> LLMExtract[LLM으로 회사 추출<br/>산업별 주요 회사 목록]
    LLMExtract --> Validate[데이터 검증<br/>stock_code 6자리 확인]
    Validate --> CheckDartCode{dart_code 유효?}
    CheckDartCode -->|아니오| MapDartCode[매핑 테이블에서<br/>dart_code 조회<br/>corpCode.xml]
    CheckDartCode -->|예| AddCompany[회사 추가]
    MapDartCode --> AddCompany
    AddCompany --> LoopIndustry
    LoopIndustry -->|완료| Return[companies_by_industry 반환<br/>stock_code, stock_name, dart_code, reasoning]
    Return --> End([종료])
```

#### 5. fetch_financial_data
```mermaid
flowchart TD
    Start([시작]) --> GetCompanies[companies_by_industry 가져오기]
    GetCompanies --> LoopCompany{각 회사별 반복}
    LoopCompany --> CheckDB{DB에 재무 데이터<br/>존재?}
    CheckDB -->|예| GetFromDB[DB에서 조회<br/>stock_code, dart_code, bsns_year]
    CheckDB -->|아니오| CallDART[DART API 호출<br/>get_financial_statements_by_year]
    CallDART --> SaveDB[DB에 저장<br/>save_financial_to_db]
    GetFromDB --> AddFinancials[financial_data에 추가]
    SaveDB --> AddFinancials
    AddFinancials --> LoopCompany
    LoopCompany -->|완료| Return[financial_data 반환<br/>재무 지표: revenue, operating_profit, net_income 등]
    Return --> End([종료])
```

#### 6. calculate_health_factor
```mermaid
flowchart TD
    Start([시작]) --> GetFinancials[financial_data 가져오기]
    GetFinancials --> LoopCompany{각 회사별 반복}
    LoopCompany --> CalcRevenueGrowth[매출 성장률 점수<br/>가중치: 0.3]
    CalcRevenueGrowth --> CalcProfitability[수익성 점수<br/>영업이익률, 가중치: 0.3]
    CalcProfitability --> CalcStability[안정성 점수<br/>부채비율, 유동비율, 가중치: 0.2]
    CalcStability --> CalcTrend[수익성 추세 점수<br/>영업이익 성장률, 가중치: 0.2]
    CalcTrend --> WeightedAvg[가중 평균 계산<br/>health_factor = 0-1]
    WeightedAvg --> AddHealth[health_factors에 추가]
    AddHealth --> LoopCompany
    LoopCompany -->|완료| Return[health_factors 반환<br/>health_factor, calculation_details]
    Return --> End([종료])
```

#### 7. generate_report
```mermaid
flowchart TD
    Start([시작]) --> GetData[모든 데이터 가져오기<br/>selected_news, predicted_industries<br/>companies_by_industry, health_factors]
    GetData --> LLMGenerate[LLM으로 보고서 생성<br/>summary, industries, companies]
    LLMGenerate --> MergeData[실제 데이터와 병합<br/>related_news, companies 보강]
    MergeData --> CheckCompanies{LLM companies<br/>매칭 성공?}
    CheckCompanies -->|아니오| FallbackCompanies[companies_by_industry<br/>실제 회사 목록 사용]
    CheckCompanies -->|예| UseLLMCompanies[LLM 생성 회사 사용]
    FallbackCompanies --> BuildReport[report_data 구성]
    UseLLMCompanies --> BuildReport
    BuildReport --> Return[report_data 반환<br/>summary, industries, companies]
    Return --> End([종료])
```

### State 데이터 흐름

```mermaid
graph LR
    subgraph "입력"
        Input1[analysis_date]
        Input2[current_time]
    end
    
    subgraph "중간 상태"
        State1[filtered_news<br/>List NewsArticle]
        State2[selected_news<br/>List NewsArticle]
        State3[news_scores<br/>Dict int:float]
        State4[selection_reasons<br/>Dict int:str]
        State5[predicted_industries<br/>List Dict]
        State6[companies_by_industry<br/>Dict str:List Dict]
        State7[financial_data<br/>Dict str:Dict]
        State8[health_factors<br/>Dict str:Dict]
    end
    
    subgraph "최종 결과"
        Output1[report_data<br/>Dict]
        Output2[report_id<br/>Optional int]
    end
    
    Input1 --> State1
    Input2 --> State1
    State1 --> State2
    State2 --> State3
    State2 --> State4
    State2 --> State5
    State5 --> State6
    State6 --> State7
    State7 --> State8
    State2 --> Output1
    State5 --> Output1
    State6 --> Output1
    State8 --> Output1
    Output1 --> Output2
```

### 노드별 주요 기능 및 데이터 변환

| 노드 | 입력 | 출력 | 주요 기능 |
|------|------|------|----------|
| filter_news_by_date | analysis_date, current_time | filtered_news | 날짜 범위로 뉴스 필터링 (전날 6시 ~ 당일 23:59) |
| select_relevant_news | filtered_news | selected_news, news_scores, selection_reasons | Semantic Search + LLM으로 주식 영향도 높은 뉴스 선별 |
| predict_industries | selected_news | predicted_industries | LLM으로 뉴스 분석하여 유망 산업군 예측 |
| extract_companies | predicted_industries, selected_news | companies_by_industry | LLM으로 산업별 회사 추출 + dart_code 매핑 |
| fetch_financial_data | companies_by_industry | financial_data | DB 또는 DART API로 재무 데이터 조회 |
| calculate_health_factor | financial_data, companies_by_industry | health_factors | 재무 지표 기반 Health Factor 계산 |
| generate_report | selected_news, predicted_industries, companies_by_industry, health_factors | report_data | LLM으로 최종 보고서 생성 및 데이터 병합 |

---

**참고**: 이 다이어그램들은 Mermaid 문법으로 작성되었으며, GitHub, GitLab, 또는 Mermaid를 지원하는 마크다운 뷰어에서 렌더링됩니다.
