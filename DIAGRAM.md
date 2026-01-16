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
    Scheduler --> AnalysisScheduler
    Scheduler --> EmailScheduler
    NewsScheduler -->|POST /api/get_news| FastAPI
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
    }

    NEWS_ARTICLES {
        int id PK
        string title
        text meta_description
        text content
        string source
        string url
        timestamp published_at
        timestamp collected_at
        vector embedding "pgvector"
        jsonb metadata "날짜, 원문 링크 등"
    }

    REPORT_NEWS {
        int report_id FK
        int news_id FK
    }

    REPORT_INDUSTRIES {
        int id PK
        int report_id FK
        string industry_name
        string impact_level
        text impact_description
        string trend_direction
        timestamp created_at
    }

    REPORT_STOCKS {
        int id PK
        int report_id FK
        int industry_id FK
        string stock_code
        string stock_name
        string expected_trend
        decimal confidence_score
        text reasoning
        timestamp created_at
    }
```

## 🎨 Frontend 컴포넌트 구조

```mermaid
graph TD
    subgraph "Pages"
        HomePage[/ - 홈페이지]
        ReportPage[/report/:id - 보고서 상세]
    end

    subgraph "Components"
        HeroSection[HeroSection<br/>Hero 섹션]
        TodayReports[TodayReports<br/>오늘의 보고서 목록]
        ReportCard[ReportCard<br/>보고서 카드]
        NewsList[NewsList<br/>뉴스 기사 리스트]
        IndustrySection[IndustrySection<br/>산업별 분석]
        StockCard[StockCard<br/>주식 카드]
    end

    subgraph "API Layer"
        ReportsAPI[lib/api/reports.ts<br/>- getTodayReports<br/>- getReport]
    end

    HomePage --> HeroSection
    HomePage --> TodayReports
    TodayReports --> ReportCard
    ReportPage --> NewsList
    ReportPage --> IndustrySection
    IndustrySection --> StockCard
    TodayReports --> ReportsAPI
    ReportPage --> ReportsAPI
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

## 📋 주요 기능 플로우

### 자동 뉴스 수집 프로세스 (매시간)

```mermaid
flowchart TD
    Start([스케줄러: 매시간<br/>POST /api/get_news]) --> Orchestrate[Orchestration 설정]
    Orchestrate --> Split[쿼리 분리 및 OR 변환]
    Split --> LoopProviders{모든 Provider 시도?}
    
    LoopProviders -->|아니오| Fetch[API 호출 (Provider별 최대 수량)]
    Fetch --> Collect[결과 수집]
    Collect --> LoopProviders
    
    LoopProviders -->|예| Dedupe[URL 기반 중복 제거]
    Dedupe --> SaveNews[관계형 DB 저장]
    SaveNews --> Embedding[벡터 임베딩 생성]
    Embedding --> SaveVector[pgvector에 저장]
    SaveVector --> Success1[수집 완료]
    
    Success1 --> End([종료])
```

### 자동 일일 분석 프로세스 (매일 아침 6시)

```mermaid
flowchart TD
    Start([스케줄러: 매일 6시<br/>POST /api/analyze]) --> Query[벡터 DB에서<br/>전날 6시~현재 뉴스 조회]
    Query --> Check{뉴스 존재?}
    
    Check -->|없음| NoNews[뉴스 없음 로깅]
    Check -->|있음| Aggregate[뉴스 취합]
    
    Aggregate --> Analyze[AI 분석]
    Analyze --> OpenAI[OpenAI API 호출<br/>LLM 보고서 작성]
    OpenAI -->|성공| Parse[결과 파싱]
    OpenAI -->|실패| Error1[에러 로깅]
    
    Parse --> SaveReport[보고서 저장]
    SaveReport --> SaveIndustries[산업 분석 저장]
    SaveIndustries --> SaveStocks[주식 분석 저장]
    SaveStocks --> Success[분석 완료]
    
    NoNews --> End([종료])
    Error1 --> End
    Success --> End
```

### 수동 분석 프로세스 (선택사항)

```mermaid
flowchart TD
    Start([사용자 요청]) --> Validate{날짜 검증}
    Validate -->|유효하지 않음| Error1[에러 반환]
    Validate -->|유효함| Check{이미 분석됨?}

    Check -->|예, force=false| Return[기존 보고서 반환]
    Check -->|아니오 또는 force=true| Query[지정 기간 뉴스 조회]

    Query --> Aggregate[뉴스 취합]
    Aggregate --> Analyze[AI 분석]
    Analyze --> OpenAI[OpenAI API 호출]
    OpenAI -->|성공| Parse[결과 파싱]
    OpenAI -->|실패| Error2[에러 반환]

    Parse --> SaveReport[보고서 저장]
    SaveReport --> SaveIndustries[산업 분석 저장]
    SaveIndustries --> SaveStocks[주식 분석 저장]
    SaveStocks --> Success[성공 응답]

    Error1 --> End([종료])
    Error2 --> End
    Return --> End
    Success --> End
```

### 보고서 조회 프로세스

```mermaid
flowchart TD
    Start([사용자 요청]) --> Route{라우트 확인}

    Route -->|/| Home[홈페이지]
    Route -->|/report/:id| Detail[상세 페이지]

    Home --> FetchToday[오늘의 보고서 조회]
    FetchToday --> Query1[DB 쿼리: analysis_date = today]
    Query1 --> Join1[관계 조인: news_count, industry_count]
    Join1 --> ReturnList[목록 반환]
    ReturnList --> RenderCards[카드 렌더링]

    Detail --> FetchDetail[보고서 상세 조회]
    FetchDetail --> Query2[DB 쿼리: report_id]
    Query2 --> Join2[관계 조인: news, industries, stocks]
    Join2 --> ReturnDetail[상세 데이터 반환]
    ReturnDetail --> RenderDetail[상세 페이지 렌더링]

    RenderCards --> End([종료])
    RenderDetail --> End
```

### 이메일 전송 프로세스 (매일 아침 7시)

```mermaid
flowchart TD
    Start([스케줄러: 매일 7시<br/>POST /api/send-email]) --> GetReport[오늘 생성된 보고서 조회]
    GetReport --> GetSubscribers[구독자 이메일 목록 조회]
    GetSubscribers --> Check{보고서 및 구독자 존재?}
    
    Check -->|없음| NoData[데이터 없음 로깅]
    Check -->|있음| Loop[각 구독자에게 반복]
    
    Loop --> CreateEmail[이메일 생성<br/>보고서 링크 포함]
    CreateEmail --> SendEmail[이메일 API 호출<br/>SendGrid/Resend]
    SendEmail -->|성공| Next[다음 구독자]
    SendEmail -->|실패| Error1[에러 로깅]
    
    Next --> CheckLoop{더 많은 구독자?}
    CheckLoop -->|예| Loop
    CheckLoop -->|아니오| Success[전송 완료]
    
    NoData --> End([종료])
    Error1 --> End
    Success --> End
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

## 📦 컴포넌트 의존성

```mermaid
graph LR
    subgraph "Frontend Dependencies"
        NextJS --> React
        NextJS --> Tailwind
        NextJS --> TypeScript
        React --> Shadcn
        Tailwind --> PostCSS
    end

    subgraph "Backend Dependencies"
        FastAPI --> SQLAlchemy
        FastAPI --> Pydantic
        FastAPI --> Requests
        FastAPI --> APScheduler
        SQLAlchemy --> PostgreSQL
        PostgreSQL --> pgvector
        Requests --> OpenAI
        Requests --> NewsDataAPI
    end
```

## 🚀 배포 아키텍처 (현재: 로컬 개발)

```mermaid
graph TB
    subgraph "Local Development"
        Docker[Docker Compose]
        Docker --> Frontend[Frontend Container]
        Docker --> Backend[Backend Container]
        Docker --> DB[PostgreSQL Container]
        Docker --> Admin[Adminer Container]
    end

    subgraph "External APIs"
        Naver[네이버 뉴스 API]
        OpenAI[OpenAI API]
        Email[이메일 API<br/>SendGrid/Resend]
    end

    Backend --> NewsData
    Backend --> OpenAI
    Backend --> Email
    Backend --> DB
    Frontend --> Backend
    Admin --> DB
```

---

## 📝 다이어그램 설명

### 시스템 아키텍처

- 전체 시스템의 레이어 구조를 보여줍니다
- 클라이언트부터 데이터베이스까지의 흐름을 표현합니다

### 데이터 흐름도

- 시퀀스 다이어그램으로 요청-응답 플로우를 시각화합니다
- 자동 뉴스 수집, 일일 분석, 이메일 전송, 보고서 조회의 주요 플로우를 다룹니다

### API 엔드포인트 구조

- FastAPI 서버의 주요 엔드포인트와 요청/응답 형식을 보여줍니다

### 데이터베이스 스키마

- ER 다이어그램으로 테이블 간 관계를 표현합니다
- 외래키와 관계를 명확히 표시합니다

### Frontend 컴포넌트 구조

- Next.js 페이지와 컴포넌트의 계층 구조를 보여줍니다
- 컴포넌트 간 의존성을 표현합니다

### 주요 기능 플로우

- 플로우차트로 비즈니스 로직의 실행 순서를 표현합니다
- 조건 분기와 에러 처리를 포함합니다

---

**참고**: 이 다이어그램들은 Mermaid 문법으로 작성되었으며, GitHub, GitLab, 또는 Mermaid를 지원하는 마크다운 뷰어에서 렌더링됩니다.
