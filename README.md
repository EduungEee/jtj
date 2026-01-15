# 📈 뉴스 기반 주식 동향 분석 서비스 [market-report.today](http://market-report.today)

뉴스 데이터를 분석하여 유망 산업을 파악하고, 분석 결과를 보고서로 제공하는 서비스입니다.

## 🎯 프로젝트 개요

최신 뉴스를 수집하고 AI를 활용하여 주식 시장 동향을 분석합니다. 단순히 뉴스 내용을 파악하는 것을 넘어, 각 뉴스 기사로 인한 **사회적 파급효과**를 예측하고, 그로 인해 영향을 받는 **산업과 주식**을 분석합니다. 분석 결과를 웹 보고서로 생성하고, 사용자에게 이메일로 전송합니다. 사용자는 이메일 링크를 통해 상세한 분석 보고서를 확인할 수 있습니다.

## ✨ 주요 기능

- 📰 **자동 뉴스 수집**: 매시간 여러 뉴스 API를 통해 최신 뉴스 자동 수집 (NewsData, Naver, NewsAPI.org, TheNewsAPI)
  - **Orchestration**: 각 API의 사양에 따른 쿼리 변환 (OR 연산자 지원 등) 및 모든 Provider에서 최대 개수 수집 (Max Collection)
  - **Provider 아키텍처**: 각 Provider 클래스에 fetch 로직 통합, 공통 헬퍼 함수로 중복 제거
  - title, description 데이터 추출 및 pgvector/PostgreSQL 저장
- 🤖 **자동 보고서 생성**: 매일 아침 6시에 보고서 생성
  - 보고서 생성 시점으로부터 24시간 전의 뉴스 기사들을 활용
  - LLM을 사용하여 주식 동향 예측 분석
  - 뉴스 기사 내용 분석 및 사회적 파급효과 예측
  - 영향받는 산업 및 주식 분석
- 📧 **이메일 전송**: 매일 아침 7시에 생성된 보고서 링크를 사용자 이메일로 자동 전송

## 🛠 기술 스택 (MVP)

- **Backend**: FastAPI, PostgreSQL + pgvector (Vector DB), OpenAI API
- **Scheduler**: APScheduler (백그라운드 작업, 가볍고 FastAPI 통합 용이)
- **Frontend**: Next.js 15 (App Router)
- **기타**: Docker Compose, news API(NewsData, Naver, NewsAPI.org, TheNewsAPI), SendGrid/Resend (이메일 API)

## 🚀 빠른 시작

```bash
# 1. 환경 변수 설정
cp .env.example .env
# .env 파일에 API 키 설정

# 2. Backend와 Database 실행 (Docker)
docker-compose up -d

# 3. Backend 잘 실행됐는지 확인
docker-compose logs -f backend

# 3. Frontend 실행 (로컬)
cd frontend
npm install
npm run dev

# 4. 접속
# Frontend: http://localhost:3000
# Backend API (Swagger): http://localhost:8000/docs
# 데이터베이스 관리: http://localhost:8081 (PgWeb)

# docker-compose 재빌드
docker-compose build --no-cache
```

## 📝 API 엔드포인트

### 뉴스 관련

- `POST /api/get_news` - 뉴스 수집 엔드포인트
  - 멀티 Provider 아키텍처를 통한 뉴스 데이터 수집
  - 콤마(`,`)로 구분된 쿼리 처리 (OR 연산 지원 API 자동 변환)
  - 모든 Provider에서 최대 개수 수집 (Max Collection 전략)
  - 관계형 DB와 벡터 DB에 저장 (벡터 DB에는 날짜, 원문 링크 등 metadata 포함)
  - 1시간 마다 크론잡으로 트리거됨
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
  - 아침 6시에 트리거 됨

### 이메일 관련

- `POST /api/send-email` - 이메일 전송 엔드포인트
  - 오늘 생성된 보고서 링크를 구독자 이메일로 전송
  - 외부 이메일 API 사용 (SendGrid/Resend)
  - 아침 7시에 크론잡으로 트리거됨
- `POST /api/subscribe` - 이메일 구독
  - 사용자 이메일 주소를 구독 목록에 추가

### 자동 스케줄러

- **뉴스 수집**: 매시간 자동 실행 (`POST /api/get_news` 호출)
  - 멀티 API Provider Orchestration을 통한 뉴스 수집
  - 쿼리 변환 및 모든 Provider에서 최대 개수 수집 (Max Collection)
  - 관계형 DB와 벡터 DB에 저장 (벡터 DB metadata: 날짜, 원문 링크 리스트)
- **보고서 생성**: 매일 아침 6시 자동 실행 (`POST /api/analyze` 호출)
  - 벡터 DB에서 전날 아침 6시~현재 시간 사이의 뉴스 기사 조회
  - 조회된 뉴스 기사들을 LLM에 전달하여 주식 동향 예측 보고서 작성
- **이메일 전송**: 매일 아침 7시 자동 실행 (`POST /api/send-email` 호출)
  - 오늘 생성된 보고서 링크를 구독자 이메일로 전송
  - 외부 이메일 API 사용 (SendGrid/Resend)

## 🔧 환경 변수

```env
OPENAI_API_KEY=your_openai_api_key
# News API Keys
NEWSDATA_API_KEY=your_newsdata_api_key
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
NEWSORG_API_KEY=your_newsorg_api_key
THENEWSAPI_API_KEY=your_thenewsapi_api_key

DATABASE_URL=postgresql://postgres:postgres@postgres:5432/stock_analysis
# 이메일 API (SendGrid 또는 Resend 중 선택)
SENDGRID_API_KEY=your_sendgrid_api_key
# 또는
RESEND_API_KEY=your_resend_api_key
FRONTEND_URL=http://localhost:3000
```

---

## 기여자

- 박우림
- 송민규
- 류재상
