# 🚀 MVP 구현 계획서

해커톤을 위한 최소 기능 구현 계획서입니다.

## 📋 목표

3-5일 내에 동작하는 MVP를 완성합니다.

## 🎯 핵심 기능 (MVP)

1. ✅ **자동 뉴스 수집**: 1시간마다 newsdata.io API로 최신 뉴스 수집
   - title, description 데이터 추출
   - pgvector와 PostgreSQL에 각각 저장
2. ✅ **Vector DB 저장**: 수집된 뉴스의 meta description을 pgvector를 사용하여 PostgreSQL에 벡터 저장
3. ✅ **자동 AI 분석**: 매일 아침 6시에 보고서 생성
   - 보고서 생성 시점으로부터 24시간 전의 뉴스 기사들을 활용
   - LLM을 사용하여 주식 동향 예측 분석
4. ✅ **보고서 생성 및 저장**: 분석 결과를 보고서로 생성하여 DB에 저장
5. ✅ **웹에서 보고서 조회**: 생성된 보고서를 웹에서 조회
   - 가입한 회원: 전체 보고서 내용 조회 가능
   - 비회원: 일부 정보 흐리게 처리 및 가입 유도
6. ✅ **회원 인증 및 관리**: Clerk를 이용한 회원가입/로그인
   - 회원가입 및 로그인
   - 회원탈퇴 기능
   - 이메일 변경 설정 (이메일 verification 필요)
7. ⚠️ **이메일 전송**: 매일 아침 7시에 생성된 보고서 링크를 사용자 이메일로 자동 전송 (외부 이메일 API 사용: SendGrid/Resend)

## 📅 일정 (5일 기준)

### Day 1: Backend 기본 구조 + DB

**목표**: FastAPI 서버 실행, DB 연결

- [x] 프로젝트 구조 생성
- [x] Docker Compose 설정
- [x] PostgreSQL 연결
- [x] SQLAlchemy 모델 정의
  - [x] `news_articles` 테이블
  - [x] `reports` 테이블
  - [x] `report_industries` 테이블
  - [x] `report_stocks` 테이블
- [x] 데이터베이스 스키마 초기화
  - [x] `app/main.py`에서 `Base.metadata.create_all(bind=engine)` 실행
  - [x] pgvector 확장 설치 (`app/database.py` 또는 초기화 스크립트)
  - [x] 애플리케이션 시작 시 자동 테이블 생성
- [x] FastAPI 기본 구조 (`main.py`)
- [x] 헬스 체크 API (`GET /api/health`)

**체크포인트**: `http://localhost:8000/docs` 접속 가능

---

### Day 2: 뉴스 수집 + Vector DB + 스케줄러

**목표**: 자동 뉴스 수집 및 Vector DB 저장 파이프라인

- [x] 뉴스 API 연동 (`app/news.py`)
  - [x] newsdata.io API 연동 (최신 뉴스 데이터 가져오기)
  - [x] 뉴스 데이터에서 title, description 추출 함수
  - [x] 뉴스 저장 함수 (title, description 포함)
- [x] 뉴스 수집 API 엔드포인트 (`routers/news.py`)
  - [x] `POST /api/get_news` 엔드포인트 구현 (뉴스 수집)
    - [x] newsdata.io API로 최신 뉴스 데이터 수집
    - [x] 뉴스 데이터에서 title, description 추출
    - [x] 관계형 DB (PostgreSQL)에 저장
    - [ ] 벡터 DB (pgvector)에 저장 (metadata 포함)
  - [x] `GET /api/news` 엔드포인트 구현 (저장된 뉴스 조회)
    - [x] DB에 저장된 뉴스 기사 목록 조회
    - [x] 필터링 옵션 (날짜, 키워드 등)
- [x] pgvector 설정
  - [x] PostgreSQL에 pgvector 확장 설치
    - [x] Docker Compose에서 pgvector 포함된 PostgreSQL 이미지 사용 또는 확장 설치
    - [x] `CREATE EXTENSION IF NOT EXISTS vector;` 실행
  - [x] 뉴스 메타데이터 벡터 저장 스키마 설계
    - [x] `news_articles` 테이블에 `embedding vector(1536)` 컬럼 추가
    - [x] `metadata JSONB` 컬럼 추가 (날짜, 원문 링크 등)
  - [x] 벡터 임베딩 생성 및 저장 함수
    - [x] OpenAI Embedding API 연동 (text-embedding-ada-002 또는 text-embedding-3-small)
    - [x] meta description 기반 임베딩 생성
    - [x] pgvector에 벡터 저장 함수 구현
  - [x] 벡터 DB metadata 설계 (날짜, 원문 링크 리스트 포함)
    - [x] LLM이 날짜를 파악할 수 있도록 날짜 정보 포함 (`published_date`)
    - [x] 참조한 기사의 원문 링크 리스트 포함 (`source_url`)
    - [x] 수집 시간 정보 포함 (`collected_at`)
- [ ] 스케줄러 구현 (`app/scheduler.py`)
  - [ ] 1시간마다 `POST /api/get_news` 엔드포인트 호출하는 크론잡
  - [ ] 매일 아침 6시 보고서 생성 스케줄러
  - [ ] 매일 아침 7시 이메일 전송 스케줄러
- [ ] Background Tasks 설정 (APScheduler 사용)
  - [ ] APScheduler 설치 및 설정
  - [ ] FastAPI 앱 시작 시 스케줄러 초기화
  - [ ] 비동기 작업 스케줄링 (AsyncIOScheduler)

**체크포인트**: 자동 뉴스 수집 및 Vector DB 저장 동작

**참고사항:**

- 벡터 DB metadata 구조 예시:
  ```json
  {
    "published_date": "2024-01-15T10:30:00Z",
    "source_url": "https://newsdata.io/article/123456",
    "title": "뉴스 제목",
    "collected_at": "2024-01-15T11:00:00Z"
  }
  ```
- LLM이 날짜를 파악하고 참조 기사 링크를 확인할 수 있도록 metadata 설계 중요
- **스케줄러 선택**: APScheduler 사용 (가볍고 FastAPI 통합 용이, 별도 메시지 브로커 불필요)

---

### Day 2.5: AI 분석 파이프라인

**목표**: 일일 자동 분석 프로세스

- [ ] 벡터 DB에서 뉴스 조회 (`app/analysis.py`)
  - [ ] 현재 시간에서 전날 아침 6시 사이의 뉴스 기사 조회 (벡터 DB에서)
  - [ ] 날짜 필터링 함수 (metadata의 published_date 활용)
- [ ] OpenAI API 연동 (`app/analysis.py`)
  - [ ] 프롬프트 작성
  - [ ] 조회된 뉴스 기사들을 LLM에 전달
  - [ ] LLM이 보고서 작성 (주식 동향 예측 분석)
  - [ ] 산업/주식 분석 함수
- [ ] 분석 결과 저장
- [ ] 일일 분석 스케줄러 연동

**체크포인트**: 매일 6시 자동 분석 (전날 아침 6시~현재 뉴스 활용) → DB 저장 플로우 동작

---

### Day 3: Clerk 인증 + 보고서 API + Frontend 기본

**목표**: Clerk 인증 설정, 보고서 조회 API 및 Frontend 기본 구조

**Backend:**

- [x] 보고서 조회 API (`GET /api/report/{report_id}`)
- [x] 오늘의 보고서 API (`GET /api/reports/today`)
- [ ] Clerk 인증 미들웨어 설정
  - [ ] Clerk Backend API 연동
  - [ ] 인증된 사용자만 전체 보고서 조회 가능하도록 권한 체크

**Frontend:**

- [x] Next.js 15 프로젝트 초기화
- [x] Tailwind 4 CSS 설정
- [x] shadcn/ui 설정
- [ ] Clerk 설정
  - [ ] Clerk Provider 설정 (`app/layout.tsx`)
  - [ ] 환경 변수 설정 (`VITE_CLERK_PUBLISHABLE_KEY` 또는 `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`)
  - [ ] SignIn, SignUp 컴포넌트 추가
  - [ ] UserButton 컴포넌트 추가
- [x] 레이아웃 구조 (`app/layout.tsx`)
- [x] API 클라이언트 함수 (`lib/api/reports.ts`)
- [x] 홈페이지 기본 구조 (`app/page.tsx`)

**체크포인트**: Clerk 인증 동작 및 Frontend에서 Backend API 호출 성공

---

### Day 4: Frontend 페이지 구현 + 인증 기능

**목표**: 홈페이지, 보고서 상세 페이지 및 인증 기능

- [x] 홈페이지 구현
  - [x] Hero 섹션
  - [x] 오늘의 보고서 목록 (`components/TodayReports.tsx`)
  - [x] 보고서 카드 컴포넌트
- [x] 보고서 상세 페이지 (`app/report/[id]/page.tsx`)
  - [x] 보고서 헤더
  - [x] 뉴스 기사 리스트
  - [x] 산업별 분석 섹션
  - [x] 주식 카드 컴포넌트
- [ ] 인증 기능 구현
  - [ ] 비회원용 UI: 일부 정보 흐리게 처리 (blur 효과)
  - [ ] 가입 유도 컴포넌트 (회원가입 버튼, CTA)
  - [ ] 회원용 UI: 전체 보고서 내용 표시
  - [ ] 사용자 프로필 페이지 (`app/profile/page.tsx`)
    - [ ] 회원탈퇴 기능
    - [ ] 이메일 변경 설정 (Clerk 이메일 verification 활용)
    - [ ] UserProfile 컴포넌트 또는 커스텀 UI

**체크포인트**: 전체 플로우 동작 (홈 → 보고서 상세), 인증 기능 동작 확인

---

### Day 5: 통합 테스트 + 버그 수정

**목표**: 전체 기능 테스트 및 최종 수정

- [ ] 전체 플로우 테스트
  - [ ] 뉴스 수집 → 분석 → 보고서 생성
  - [ ] Frontend에서 보고서 조회
- [ ] 버그 수정
- [ ] UI/UX 개선
- [ ] 이메일 기능
  - [ ] 외부 이메일 API 연동 (SendGrid/Resend)
  - [ ] 이메일 구독 API (`POST /api/subscribe`)
  - [ ] 이메일 전송 API 엔드포인트 (`POST /api/send-email`)
  - [ ] 이메일 전송 기능 (`app/email.py`)
  - [ ] 매일 아침 7시 이메일 전송 스케줄러 연동 (`POST /api/send-email` 호출)
- [ ] Clerk 인증 기능 통합
  - [ ] Backend에서 Clerk 인증 미들웨어 설정
  - [ ] 회원/비회원 구분 로직 구현
  - [ ] 비회원용 흐림 처리 및 가입 유도 UI 구현
  - [ ] 회원탈퇴 처리 로직 (Clerk webhook 또는 직접 처리)
  - [ ] 이메일 변경 verification 확인

**체크포인트**: 데모 가능한 상태

---

## 🗂 프로젝트 구조

```
jtj/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 앱 (스키마 초기화 포함)
│   │   ├── database.py      # DB 연결 및 초기화 (pgvector 확장 설치)
│   │   ├── news.py          # 뉴스 수집
│   │   ├── analysis.py      # AI 분석
│   │   ├── scheduler.py     # 스케줄러 (뉴스 수집, 일일 분석)
│   │   ├── vector_store.py  # Vector DB 저장 (pgvector)
│   │   ├── report.py        # 보고서 생성
│   │   └── email.py         # 이메일 전송 로직 (외부 API)
│   ├── models/
│   │   └── models.py        # SQLAlchemy 모델
│   ├── routers/
│   │   ├── reports.py       # 보고서 API
│   │   ├── analyze.py       # 분석 API (벡터 DB에서 뉴스 조회 후 LLM 보고서 작성)
│   │   ├── news.py          # 뉴스 API (POST /api/get_news: 수집, GET /api/news: 조회)
│   │   └── email.py         # 이메일 API (POST /api/send-email, POST /api/subscribe)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx         # 홈페이지
│   │   ├── profile/
│   │   │   └── page.tsx     # 사용자 프로필 (회원탈퇴, 이메일 변경)
│   │   └── report/
│   │       └── [id]/
│   │           └── page.tsx # 보고서 상세
│   ├── components/
│   │   ├── TodayReports.tsx
│   │   ├── StockCard.tsx
│   │   ├── SignInPrompt.tsx  # 가입 유도 컴포넌트
│   │   └── BlurredContent.tsx # 비회원용 흐림 처리 컴포넌트
│   ├── lib/
│   │   ├── api/
│   │   │   └── reports.ts    # API 클라이언트
│   │   └── clerk.ts          # Clerk 유틸리티
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── .env.example
```

## 🔧 기술 스택 상세

### Backend

- **Framework**: FastAPI
- **Database**: PostgreSQL 15 + pgvector (Vector DB)
- **ORM**: SQLAlchemy
- **Scheduler**: APScheduler (백그라운드 작업, 가볍고 FastAPI 통합 용이)
- **AI**: OpenAI API
- **Email**: SendGrid 또는 Resend API (외부 이메일 서비스)

### Frontend

- **Framework**: Next.js 15 (App Router)
- **Styling**: Tailwind CSS
- **Authentication**: Clerk (회원가입, 로그인, 이메일 verification)

### Infrastructure

- **Containerization**: Docker & Docker Compose

### 스키마 정의

```sql
-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 뉴스 기사
CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    meta_description TEXT,  -- meta description 데이터
    content TEXT,
    source VARCHAR(255),
    url VARCHAR(1000),
    published_at TIMESTAMP,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding vector(1536),  -- OpenAI embedding 차원 (meta description 기반, text-embedding-ada-002 또는 text-embedding-3-small)
    metadata JSONB  -- 벡터 DB metadata (날짜, 원문 링크 리스트 등 LLM 참조용 정보)
);

-- 보고서
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_date DATE NOT NULL
);

-- 보고서-뉴스 연결
CREATE TABLE report_news (
    report_id INTEGER REFERENCES reports(id),
    news_id INTEGER REFERENCES news_articles(id),
    PRIMARY KEY (report_id, news_id)
);

-- 산업 분석
CREATE TABLE report_industries (
    id SERIAL PRIMARY KEY,
    report_id INTEGER REFERENCES reports(id),
    industry_name VARCHAR(255) NOT NULL,
    impact_level VARCHAR(50),
    trend_direction VARCHAR(50)
);

-- 주식 분석
CREATE TABLE report_stocks (
    id SERIAL PRIMARY KEY,
    report_id INTEGER REFERENCES reports(id),
    industry_id INTEGER REFERENCES report_industries(id),
    stock_code VARCHAR(50),
    stock_name VARCHAR(255),
    expected_trend VARCHAR(50),
    confidence_score DECIMAL(3,2),
    reasoning TEXT
);

-- 이메일 구독 (선택사항 - Clerk 사용 시 Clerk의 사용자 정보 활용 가능)
CREATE TABLE email_subscriptions (
    id SERIAL PRIMARY KEY,
    clerk_user_id VARCHAR(255) UNIQUE,  -- Clerk 사용자 ID
    email VARCHAR(255) NOT NULL,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

## 🔌 API 엔드포인트 (MVP)

### 뉴스 관련

- `POST /api/get_news` - 뉴스 수집 엔드포인트
  - newsdata.io API로 최신 뉴스 데이터 수집
  - 뉴스 데이터에서 title, description 추출
  - 관계형 DB와 벡터 DB에 저장 (벡터 DB에는 날짜, 원문 링크 등 metadata 포함)
  - 1시간마다 크론잡으로 트리거됨
- `GET /api/news` - 저장된 뉴스 조회 엔드포인트
  - DB에 저장된 뉴스 기사 목록 조회
  - 필터링 옵션 (날짜, 키워드 등)

### 보고서 관련

- `GET /api/reports/today` - 오늘의 보고서 목록
- `GET /api/report/{report_id}` - 보고서 상세
- `POST /api/analyze` - 뉴스 분석 및 보고서 작성
  - 벡터 DB에서 현재 시간~전날 아침 6시 사이의 뉴스 기사 조회
  - 조회된 뉴스 기사들을 LLM에 전달하여 보고서 작성
  - 분석 결과(보고서)를 DB에 저장
  - 아침 6시에 트리거됨

### 이메일 관련

- `POST /api/send-email` - 이메일 전송 엔드포인트
  - 오늘 생성된 보고서 링크를 구독자 이메일로 전송
  - 외부 이메일 API 사용 (SendGrid/Resend)
  - 아침 7시에 크론잡으로 트리거됨
- `POST /api/subscribe` - 이메일 구독
  - 사용자 이메일 주소를 구독 목록에 추가

### 인증 관련 (Clerk)

- Clerk가 자동으로 제공하는 엔드포인트:
  - `/sign-in` - 로그인 페이지
  - `/sign-up` - 회원가입 페이지
  - `/user` - 사용자 프로필 (이메일 변경, 회원탈퇴 등)
- 커스텀 API (선택사항):
  - `GET /api/user/profile` - 사용자 프로필 정보 조회
  - `DELETE /api/user/account` - 회원탈퇴 처리 (Clerk webhook 활용)

### 자동 스케줄러

- **뉴스 수집**: 매시간 자동 실행 (`POST /api/get_news` 호출)
  - newsdata.io API로 최신 뉴스 데이터 수집
  - 뉴스 데이터에서 title, description 추출
  - 관계형 DB와 벡터 DB에 저장 (벡터 DB metadata: 날짜, 원문 링크 리스트)
- **보고서 생성**: 매일 아침 6시 자동 실행 (`POST /api/analyze` 호출)
  - 벡터 DB에서 전날 아침 6시~현재 시간 사이의 뉴스 기사 조회
  - 조회된 뉴스 기사들을 LLM에 전달하여 주식 동향 예측 보고서 작성
- **이메일 전송**: 매일 아침 7시 자동 실행 (`POST /api/send-email` 호출)
  - 오늘 생성된 보고서 링크를 구독자 이메일로 전송
  - 외부 이메일 API 사용 (SendGrid/Resend)

## 🎨 Frontend 페이지 (MVP)

### 필수

- `/` - 홈페이지 (오늘의 보고서 목록)
- `/report/[id]` - 보고서 상세 페이지
  - 회원: 전체 내용 표시
  - 비회원: 일부 정보 흐리게 처리 + 가입 유도
- `/profile` - 사용자 프로필 페이지
  - 회원탈퇴 기능
  - 이메일 변경 설정 (이메일 verification)

### 선택

- 이메일 구독 폼 (홈페이지에 추가)

## 🔧 환경 변수

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key

# NewsData.io API
NEWSDATA_API_KEY=your_newsdata_api_key

# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/stock_analysis

# 이메일 API (SendGrid 또는 Resend 중 선택)
SENDGRID_API_KEY=your_sendgrid_api_key
# 또는
RESEND_API_KEY=your_resend_api_key

# Frontend URL
FRONTEND_URL=http://localhost:3000

# Clerk 인증 (Frontend)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key
```

## ⚡ 빠른 시작 체크리스트

### 초기 설정

- [ ] Git 저장소 생성
- [ ] `.env.example` 파일 생성
- [ ] `docker-compose.yml` 작성
- [ ] Backend `Dockerfile` 작성
- [ ] Frontend `Dockerfile` 작성

### Backend

- [ ] `requirements.txt` 작성
- [ ] FastAPI 앱 초기화
- [ ] DB 모델 정의
- [ ] 기본 API 라우터

### Frontend

- [ ] Next.js 15 프로젝트 생성
- [ ] Tailwind CSS 설정
- [ ] Clerk 설정
  - [ ] `@clerk/nextjs` 패키지 설치
  - [ ] Clerk Provider 설정 (`app/layout.tsx`)
  - [ ] 환경 변수 설정 (`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`)
  - [ ] SignIn, SignUp 컴포넌트 추가
  - [ ] UserButton 컴포넌트 추가
- [ ] 기본 레이아웃

## 🐛 문제 해결 가이드

### DB 연결 실패

- Docker Compose에서 postgres 서비스 확인
- `DATABASE_URL` 환경 변수 확인

### OpenAI API 에러

- API 키 확인
- Rate limit 확인
- 프롬프트 최적화 (토큰 수 줄이기)

### 이메일 API 에러

- SendGrid/Resend API 키 확인
- Rate limit 확인 (무료 티어 제한 확인)
- 이메일 템플릿 형식 확인
- 발신자 이메일 도메인 인증 확인 (SendGrid/Resend)

### Frontend-Backend 연결 실패

- CORS 설정 확인
- `NEXT_PUBLIC_API_URL` 환경 변수 확인
- 네트워크 요청 확인 (브라우저 DevTools)

### Clerk 인증 에러

- Clerk Publishable Key 확인 (`VITE_CLERK_PUBLISHABLE_KEY` 또는 `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`)
- Clerk Dashboard에서 애플리케이션 설정 확인
- 이메일 verification 설정 확인
- 회원탈퇴 시 관련 데이터 정리 로직 확인

## 📝 개발 팁

1. **우선순위**: 핵심 기능부터 구현
2. **테스트**: 각 단계마다 동작 확인
3. **에러 처리**: 기본적인 에러 처리만 (MVP)
4. **UI**: 최소한의 스타일링 (Tailwind 기본 클래스)
5. **데이터**: Mock 데이터로 먼저 테스트
6. **이메일**: 외부 API 사용 (SendGrid 무료 티어 또는 Resend 무료 티어 활용)
7. **인증**: Clerk 사용 (회원가입, 로그인, 이메일 verification 자동 처리)
8. **권한 관리**: 회원/비회원 구분하여 보고서 접근 제어

## 🎯 MVP 완성 기준

- [ ] 1시간마다 자동 뉴스 수집 동작 (`POST /api/get_news` 호출)
- [ ] newsdata.io API로 최신 뉴스 데이터 수집 및 title, description 추출
- [ ] 뉴스 title, description을 관계형 DB와 벡터 DB에 저장
- [ ] 벡터 DB에 날짜 및 원문 링크 리스트를 포함한 metadata 저장 (LLM 참조용)
- [ ] 매일 아침 6시에 벡터 DB에서 전날 아침 6시~현재 시간 뉴스 기사 조회 후 LLM 보고서 작성
- [ ] AI 분석 결과 생성 및 보고서 DB 저장
- [ ] 매일 아침 7시에 이메일 자동 전송 (`POST /api/send-email` 호출)
- [ ] Clerk 인증 기능 동작 (회원가입, 로그인)
- [ ] 회원탈퇴 기능 동작
- [ ] 이메일 변경 및 verification 동작
- [ ] 회원/비회원 구분하여 보고서 접근 제어 동작
- [ ] Frontend에서 보고서 조회 가능
- [ ] 전체 자동화 플로우 동작 확인

---

**해커톤 MVP** - 빠르게 동작하는 프로토타입 완성!
