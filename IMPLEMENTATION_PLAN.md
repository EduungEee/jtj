# 📋 구현 계획서

뉴스 기반 주식 동향 분석 서비스 구현을 위한 상세 계획서입니다.

## 📌 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [기술 스택 및 아키텍처](#기술-스택-및-아키텍처)
3. [데이터베이스 스키마 설계](#데이터베이스-스키마-설계)
4. [API 설계](#api-설계)
5. [프론트엔드 설계](#프론트엔드-설계)
6. [단계별 구현 계획](#단계별-구현-계획)
7. [타임라인](#타임라인)
8. [배포 계획](#배포-계획)
9. [테스트 계획](#테스트-계획)

---

## 프로젝트 개요

### 목표
- 뉴스 데이터를 수집하고 AI로 분석하여 주식 시장 동향을 예측
- 사회적 파급효과를 예측하고 영향받는 산업/주식을 분석
- 분석 결과를 웹 보고서로 제공하고 이메일로 전송

### 핵심 기능
1. 뉴스 수집 및 저장
2. AI 기반 뉴스 분석 (파급효과, 산업, 주식 예측)
3. 보고서 생성 및 저장
4. 이메일 전송
5. 웹 기반 보고서 조회

---

## 기술 스택 및 아키텍처

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy
- **AI**: OpenAI API (GPT-4)
- **Email**: SMTP (또는 SendGrid)
- **News API**: NewsAPI 또는 네이버/다음 뉴스 API

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (선택사항)

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Deployment**:
  - Frontend: Vercel
  - Backend: Railway
  - Database: Railway PostgreSQL

---

## 데이터베이스 스키마 설계

### 테이블 구조

#### 1. `users` - 사용자 정보
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

#### 2. `news_articles` - 뉴스 기사
```sql
CREATE TABLE news_articles (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    source VARCHAR(255),
    url VARCHAR(1000),
    published_at TIMESTAMP,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    category VARCHAR(100)
);
```

#### 3. `reports` - 분석 보고서
```sql
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_date DATE NOT NULL
);
```

#### 4. `report_news` - 보고서-뉴스 연결 (다대다)
```sql
CREATE TABLE report_news (
    report_id INTEGER REFERENCES reports(id) ON DELETE CASCADE,
    news_id INTEGER REFERENCES news_articles(id) ON DELETE CASCADE,
    PRIMARY KEY (report_id, news_id)
);
```

#### 5. `report_industries` - 보고서별 산업 분석
```sql
CREATE TABLE report_industries (
    id SERIAL PRIMARY KEY,
    report_id INTEGER REFERENCES reports(id) ON DELETE CASCADE,
    industry_name VARCHAR(255) NOT NULL,
    impact_level VARCHAR(50), -- 'high', 'medium', 'low'
    impact_description TEXT,
    trend_direction VARCHAR(50), -- 'positive', 'negative', 'neutral'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 6. `report_stocks` - 보고서별 주식 분석
```sql
CREATE TABLE report_stocks (
    id SERIAL PRIMARY KEY,
    report_id INTEGER REFERENCES reports(id) ON DELETE CASCADE,
    industry_id INTEGER REFERENCES report_industries(id) ON DELETE CASCADE,
    stock_code VARCHAR(50),
    stock_name VARCHAR(255),
    expected_trend VARCHAR(50), -- 'up', 'down', 'neutral'
    confidence_score DECIMAL(3,2), -- 0.00 ~ 1.00
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 7. `email_subscriptions` - 이메일 구독
```sql
CREATE TABLE email_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    report_id INTEGER REFERENCES reports(id) ON DELETE CASCADE,
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP
);
```

### 인덱스
```sql
CREATE INDEX idx_reports_analysis_date ON reports(analysis_date);
CREATE INDEX idx_news_published_at ON news_articles(published_at);
CREATE INDEX idx_report_news_report_id ON report_news(report_id);
CREATE INDEX idx_report_industries_report_id ON report_industries(report_id);
CREATE INDEX idx_report_stocks_report_id ON report_stocks(report_id);
```

---

## API 설계

### Base URL
- Development: `http://localhost:8000`
- Production: `https://[backend-domain]`

### 엔드포인트 상세

#### 1. `GET /api/reports/today`
오늘 작성된 보고서 목록 조회 (홈페이지용)

**Response:**
```json
{
  "reports": [
    {
      "id": 1,
      "title": "2024-01-15 주식 동향 분석",
      "summary": "AI 반도체 산업 급성장...",
      "created_at": "2024-01-15T10:00:00Z",
      "industries": ["반도체", "AI"],
      "main_trend": "positive"
    }
  ]
}
```

#### 2. `GET /api/report/{report_id}`
보고서 상세 조회

**Response:**
```json
{
  "id": 1,
  "title": "2024-01-15 주식 동향 분석",
  "summary": "...",
  "created_at": "2024-01-15T10:00:00Z",
  "analysis_date": "2024-01-15",
  "news_articles": [
    {
      "id": 1,
      "title": "삼성전자, AI 반도체 대량 생산",
      "source": "조선일보",
      "published_at": "2024-01-15T08:00:00Z"
    }
  ],
  "industries": [
    {
      "id": 1,
      "industry_name": "반도체",
      "impact_level": "high",
      "impact_description": "...",
      "trend_direction": "positive",
      "stocks": [
        {
          "id": 1,
          "stock_code": "005930",
          "stock_name": "삼성전자",
          "expected_trend": "up",
          "confidence_score": 0.85,
          "reasoning": "..."
        }
      ]
    }
  ],
  "insights": "..."
}
```

#### 3. `POST /api/analyze`
뉴스 분석 요청 (수동 트리거 또는 스케줄러)

**Request Body:**
```json
{
  "date": "2024-01-15",  // optional, 기본값: 오늘
  "force": false  // optional, 이미 분석된 날짜도 재분석할지 여부
}
```

**Response:**
```json
{
  "report_id": 1,
  "status": "completed",
  "message": "Analysis completed successfully"
}
```

#### 4. `POST /api/subscribe`
이메일 구독 등록

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Subscription successful"
}
```

#### 5. `POST /api/send-email`
이메일 전송 (관리자용 또는 스케줄러)

**Request Body:**
```json
{
  "report_id": 1,
  "user_ids": [1, 2, 3]  // optional, 없으면 모든 구독자에게 전송
}
```

**Response:**
```json
{
  "success": true,
  "sent_count": 10
}
```

#### 6. `GET /api/health`
헬스 체크

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

---

## 프론트엔드 설계

### 페이지 구조

#### 1. 홈페이지 (`/`)
**섹션 구성:**

1. **Hero 섹션 (가입 유도)**
   - 서비스 소개 문구
   - 가치 제안
   - 이메일 입력 폼 (구독)
   - CTA 버튼

2. **오늘의 보고서 미리보기**
   - 보고서 카드 리스트
   - 각 카드: 제목, 요약, 주요 산업 태그, 생성 시간
   - 클릭 시 `/report/[id]`로 이동

3. **분석 방식 소개**
   - 3단계 프로세스 설명
   - 각 단계별 아이콘 및 설명
   - 신뢰성 강조

**컴포넌트:**
- `HeroSection` (Client Component)
- `TodayReports` (Server Component)
- `AnalysisProcess` (Server Component)
- `EmailSubscribeForm` (Client Component)

#### 2. 보고서 상세 페이지 (`/report/[id]`)
**구성 요소:**

1. **헤더**
   - 보고서 제목
   - 생성 날짜
   - 공유 버튼

2. **요약 섹션**
   - 전체 요약 텍스트

3. **분석된 뉴스 기사**
   - 뉴스 카드 리스트
   - 각 기사: 제목, 출처, 발행일, 링크

4. **산업별 분석**
   - 산업별 섹션
   - 각 산업: 영향도, 트렌드, 관련 주식 목록
   - 주식 카드: 종목명, 코드, 예상 동향, 신뢰도, 근거

5. **투자 인사이트**
   - 종합 분석 및 추천

**컴포넌트:**
- `ReportHeader` (Server Component)
- `ReportSummary` (Server Component)
- `NewsArticlesList` (Server Component)
- `IndustryAnalysis` (Server Component)
- `StockCard` (Server Component)
- `InvestmentInsights` (Server Component)

### 공통 컴포넌트

- `Layout` - 공통 레이아웃 (헤더, 푸터)
- `Loading` - 로딩 스피너
- `ErrorBoundary` - 에러 처리
- `Button` - 재사용 가능한 버튼
- `Card` - 카드 컨테이너

### 라우팅 구조
```
app/
├── layout.tsx          # 루트 레이아웃
├── page.tsx            # 홈페이지
├── loading.tsx         # 로딩 UI
├── error.tsx           # 에러 UI
├── not-found.tsx       # 404 페이지
└── report/
    └── [id]/
        ├── page.tsx    # 보고서 상세
        ├── loading.tsx
        └── error.tsx
```

---

## 단계별 구현 계획

### Phase 1: 프로젝트 초기 설정 (1-2일)

#### 1.1 프로젝트 구조 생성
- [ ] 프로젝트 루트 디렉토리 구조 생성
- [ ] Backend 디렉토리 및 기본 파일 생성
- [ ] Frontend 디렉토리 및 Next.js 15 초기화
- [ ] `.gitignore` 파일 생성
- [ ] `.env.example` 파일 생성

#### 1.2 Docker 설정
- [ ] `docker-compose.yml` 작성
- [ ] Backend `Dockerfile` 작성
- [ ] Frontend `Dockerfile` 작성
- [ ] Docker Compose 테스트

#### 1.3 개발 환경 설정
- [ ] Backend 가상환경 설정
- [ ] `requirements.txt` 작성 (FastAPI, SQLAlchemy, psycopg2 등)
- [ ] Frontend `package.json` 설정
- [ ] TypeScript 설정
- [ ] Tailwind CSS 설정

---

### Phase 2: 데이터베이스 및 Backend 기본 구조 (2-3일)

#### 2.1 데이터베이스 모델
- [ ] SQLAlchemy 모델 정의 (`models/`)
  - [ ] User 모델
  - [ ] NewsArticle 모델
  - [ ] Report 모델
  - [ ] ReportIndustry 모델
  - [ ] ReportStock 모델
  - [ ] EmailSubscription 모델
- [ ] 관계 설정 (Foreign Key, Many-to-Many)
- [ ] 데이터베이스 마이그레이션 스크립트 작성

#### 2.2 데이터베이스 연결
- [ ] SQLAlchemy 엔진 설정
- [ ] 데이터베이스 세션 관리
- [ ] 연결 테스트

#### 2.3 FastAPI 기본 구조
- [ ] `main.py` 작성 (FastAPI 앱 초기화)
- [ ] CORS 설정
- [ ] 라우터 구조 설정
- [ ] 환경 변수 관리 (`pydantic-settings`)

#### 2.4 API 라우터 기본 구조
- [ ] `routers/` 디렉토리 생성
- [ ] `routers/reports.py` 생성
- [ ] `routers/analyze.py` 생성
- [ ] `routers/subscribe.py` 생성
- [ ] `routers/health.py` 생성

---

### Phase 3: 뉴스 수집 모듈 (2일)

#### 3.1 뉴스 API 클라이언트
- [ ] `app/news.py` 작성
- [ ] NewsAPI 또는 네이버/다음 뉴스 API 연동
- [ ] 뉴스 데이터 파싱 함수
- [ ] 에러 처리 및 재시도 로직

#### 3.2 뉴스 저장 로직
- [ ] 중복 뉴스 체크 (URL 기반)
- [ ] 데이터베이스 저장 함수
- [ ] 배치 저장 최적화

#### 3.3 뉴스 수집 스케줄러 (선택사항)
- [ ] Celery 또는 APScheduler 설정
- [ ] 주기적 뉴스 수집 작업
- [ ] 또는 수동 트리거 API 엔드포인트

---

### Phase 4: AI 분석 모듈 (3-4일)

#### 4.1 OpenAI API 연동
- [ ] `app/analysis.py` 작성
- [ ] OpenAI 클라이언트 설정
- [ ] API 키 관리

#### 4.2 프롬프트 엔지니어링
- [ ] 뉴스 분석 프롬프트 작성
- [ ] 파급효과 예측 프롬프트
- [ ] 산업/주식 분석 프롬프트
- [ ] JSON 응답 형식 정의

#### 4.3 분석 파이프라인
- [ ] 뉴스 기사 분석 함수
- [ ] 파급효과 추출 함수
- [ ] 산업 분석 함수
- [ ] 주식 분석 함수
- [ ] 결과 통합 및 구조화

#### 4.4 분석 결과 저장
- [ ] Report 생성
- [ ] ReportIndustry 저장
- [ ] ReportStock 저장
- [ ] Report-News 연결 저장

---

### Phase 5: 보고서 생성 모듈 (1-2일)

#### 5.1 보고서 생성 로직
- [ ] `app/report.py` 작성
- [ ] 보고서 제목 생성 (날짜 기반)
- [ ] 보고서 요약 생성
- [ ] 투자 인사이트 생성

#### 5.2 보고서 조회 API
- [ ] `GET /api/report/{report_id}` 구현
- [ ] 관련 데이터 조인 쿼리 최적화
- [ ] 응답 형식 정의

#### 5.3 오늘의 보고서 API
- [ ] `GET /api/reports/today` 구현
- [ ] 날짜 필터링
- [ ] 요약 정보만 반환

---

### Phase 6: 이메일 전송 모듈 (2일)

#### 6.1 이메일 설정
- [ ] `app/email.py` 작성
- [ ] SMTP 설정 또는 SendGrid API 연동
- [ ] 이메일 템플릿 작성 (HTML)

#### 6.2 이메일 전송 로직
- [ ] 구독자 목록 조회
- [ ] 보고서 링크 생성
- [ ] 이메일 전송 함수
- [ ] 전송 기록 저장

#### 6.3 이메일 API
- [ ] `POST /api/send-email` 구현
- [ ] 에러 처리 및 재시도

---

### Phase 7: 프론트엔드 - 홈페이지 (3-4일)

#### 7.1 레이아웃 및 기본 구조
- [ ] `app/layout.tsx` 작성
- [ ] 공통 헤더/푸터 컴포넌트
- [ ] Tailwind CSS 글로벌 스타일
- [ ] 메타데이터 설정

#### 7.2 Hero 섹션
- [ ] `components/HeroSection.tsx` 작성
- [ ] 서비스 소개 문구
- [ ] 이메일 구독 폼 (Client Component)
- [ ] API 연동 (`POST /api/subscribe`)

#### 7.3 오늘의 보고서 섹션
- [ ] `components/TodayReports.tsx` 작성
- [ ] `lib/api/reports.ts` - API 클라이언트 함수
- [ ] Server Component로 데이터 페칭
- [ ] 보고서 카드 컴포넌트
- [ ] 링크 연결 (`/report/[id]`)

#### 7.4 분석 방식 소개 섹션
- [ ] `components/AnalysisProcess.tsx` 작성
- [ ] 3단계 프로세스 시각화
- [ ] 아이콘 및 설명

#### 7.5 홈페이지 통합
- [ ] `app/page.tsx` 작성
- [ ] 섹션 통합 및 레이아웃
- [ ] 반응형 디자인 적용

---

### Phase 8: 프론트엔드 - 보고서 상세 페이지 (3-4일)

#### 8.1 보고서 데이터 페칭
- [ ] `lib/api/report.ts` - API 클라이언트 함수
- [ ] `app/report/[id]/page.tsx` 작성
- [ ] Server Component로 데이터 페칭
- [ ] 에러 처리 (not-found, error.tsx)

#### 8.2 보고서 헤더 컴포넌트
- [ ] `components/ReportHeader.tsx` 작성
- [ ] 제목, 날짜 표시
- [ ] 공유 기능 (선택사항)

#### 8.3 뉴스 기사 리스트
- [ ] `components/NewsArticlesList.tsx` 작성
- [ ] 뉴스 카드 컴포넌트
- [ ] 외부 링크 연결

#### 8.4 산업별 분석 컴포넌트
- [ ] `components/IndustryAnalysis.tsx` 작성
- [ ] 산업별 섹션 렌더링
- [ ] 영향도 시각화 (색상, 아이콘)

#### 8.5 주식 카드 컴포넌트
- [ ] `components/StockCard.tsx` 작성
- [ ] 종목 정보 표시
- [ ] 트렌드 방향 시각화
- [ ] 신뢰도 표시

#### 8.6 투자 인사이트 컴포넌트
- [ ] `components/InvestmentInsights.tsx` 작성
- [ ] 종합 분석 텍스트 표시

#### 8.7 보고서 페이지 통합
- [ ] 모든 컴포넌트 통합
- [ ] 로딩 상태 처리
- [ ] 반응형 디자인 적용
- [ ] SEO 최적화 (generateMetadata)

---

### Phase 9: 통합 및 테스트 (2-3일)

#### 9.1 API 통합 테스트
- [ ] 모든 API 엔드포인트 테스트
- [ ] 에러 케이스 테스트
- [ ] 데이터 검증

#### 9.2 프론트엔드 통합 테스트
- [ ] 페이지 간 네비게이션 테스트
- [ ] API 연동 테스트
- [ ] 반응형 디자인 테스트
- [ ] 브라우저 호환성 테스트

#### 9.3 전체 플로우 테스트
- [ ] 뉴스 수집 → 분석 → 보고서 생성 → 이메일 전송 플로우
- [ ] 사용자 시나리오 테스트

#### 9.4 버그 수정 및 최적화
- [ ] 성능 최적화
- [ ] 에러 처리 개선
- [ ] UI/UX 개선

---

### Phase 10: 배포 (1-2일)

#### 10.1 환경 변수 설정
- [ ] Production 환경 변수 정리
- [ ] `.env.example` 업데이트

#### 10.2 Frontend 배포 (Vercel)
- [ ] Vercel 프로젝트 생성
- [ ] GitHub 연동
- [ ] 환경 변수 설정
- [ ] 빌드 및 배포 테스트

#### 10.3 Backend 배포 (Railway)
- [ ] Railway 프로젝트 생성
- [ ] PostgreSQL 서비스 추가
- [ ] Backend 서비스 배포
- [ ] 환경 변수 설정
- [ ] 데이터베이스 마이그레이션 실행

#### 10.4 배포 후 검증
- [ ] API 연결 확인
- [ ] 데이터베이스 연결 확인
- [ ] 이메일 전송 테스트
- [ ] 전체 기능 동작 확인

---

## 타임라인

### 전체 기간: 약 20-25일 (해커톤 기준으로 압축 가능)

| Phase | 작업 내용 | 예상 기간 | 우선순위 |
|-------|----------|----------|---------|
| Phase 1 | 프로젝트 초기 설정 | 1-2일 | 높음 |
| Phase 2 | 데이터베이스 및 Backend 기본 구조 | 2-3일 | 높음 |
| Phase 3 | 뉴스 수집 모듈 | 2일 | 높음 |
| Phase 4 | AI 분석 모듈 | 3-4일 | 높음 |
| Phase 5 | 보고서 생성 모듈 | 1-2일 | 높음 |
| Phase 6 | 이메일 전송 모듈 | 2일 | 중간 |
| Phase 7 | 프론트엔드 - 홈페이지 | 3-4일 | 높음 |
| Phase 8 | 프론트엔드 - 보고서 상세 | 3-4일 | 높음 |
| Phase 9 | 통합 및 테스트 | 2-3일 | 중간 |
| Phase 10 | 배포 | 1-2일 | 높음 |

### 해커톤 압축 버전 (3-5일)

**Day 1-2: Backend 핵심 기능**
- Phase 1, 2, 3, 4, 5 (핵심만)

**Day 3: Frontend 기본**
- Phase 7, 8 (최소 기능)

**Day 4: 통합 및 배포**
- Phase 9, 10

**Day 5: 버퍼 및 개선**

---

## 배포 계획

### Frontend (Vercel)

1. **프로젝트 준비**
   - Next.js 프로젝트 확인
   - 빌드 테스트 (`npm run build`)

2. **Vercel 배포**
   - Vercel 계정 생성
   - GitHub 저장소 연결
   - 프로젝트 import
   - 빌드 설정 확인

3. **환경 변수 설정**
   ```
   NEXT_PUBLIC_API_URL=https://[backend-domain]
   ```

4. **도메인 설정** (선택사항)
   - 커스텀 도메인 연결

### Backend & Database (Railway)

1. **Railway 프로젝트 생성**
   - Railway 계정 생성
   - 새 프로젝트 생성

2. **PostgreSQL 서비스 추가**
   - PostgreSQL 템플릿 선택
   - 자동 생성된 `DATABASE_URL` 확인

3. **Backend 서비스 배포**
   - GitHub 저장소 연결
   - Dockerfile 기반 배포
   - 또는 Python 런타임 설정

4. **환경 변수 설정**
   ```
   DATABASE_URL=[Railway PostgreSQL URL]
   OPENAI_API_KEY=[your-key]
   NEWS_API_KEY=[your-key]
   SMTP_HOST=[smtp-host]
   SMTP_PORT=587
   SMTP_USER=[email]
   SMTP_PASSWORD=[password]
   FRONTEND_URL=https://[frontend-domain]
   ```

5. **데이터베이스 마이그레이션**
   - Railway CLI 또는 웹 콘솔에서 실행
   - 또는 배포 시 자동 실행 스크립트 추가

### 배포 체크리스트

- [ ] Frontend 빌드 성공
- [ ] Backend 서버 실행 확인
- [ ] 데이터베이스 연결 확인
- [ ] API 엔드포인트 동작 확인
- [ ] CORS 설정 확인
- [ ] 환경 변수 모두 설정
- [ ] 이메일 전송 테스트
- [ ] 전체 플로우 테스트

---

## 테스트 계획

### 단위 테스트

#### Backend
- [ ] 뉴스 수집 함수 테스트
- [ ] AI 분석 함수 테스트 (Mock OpenAI API)
- [ ] 보고서 생성 함수 테스트
- [ ] 이메일 전송 함수 테스트 (Mock SMTP)

#### Frontend
- [ ] API 클라이언트 함수 테스트
- [ ] 컴포넌트 렌더링 테스트 (선택사항)

### 통합 테스트

- [ ] 뉴스 수집 → 분석 → 보고서 생성 플로우
- [ ] 보고서 조회 API 테스트
- [ ] 이메일 구독 및 전송 플로우
- [ ] Frontend-Backend 연동 테스트

### E2E 테스트 (선택사항)

- [ ] 사용자 시나리오: 홈페이지 방문 → 보고서 확인
- [ ] 사용자 시나리오: 이메일 구독 → 보고서 수신 → 링크 클릭

### 수동 테스트 체크리스트

- [ ] 홈페이지 로딩 및 표시
- [ ] 오늘의 보고서 목록 표시
- [ ] 보고서 상세 페이지 표시
- [ ] 이메일 구독 기능
- [ ] 반응형 디자인 (모바일, 태블릿, 데스크톱)
- [ ] 에러 페이지 표시 (404, 500)
- [ ] 로딩 상태 표시

---

## 리스크 및 대응 방안

### 기술적 리스크

1. **OpenAI API 비용 및 제한**
   - 대응: 프롬프트 최적화, 캐싱 활용, 무료 티어 활용

2. **뉴스 API 제한**
   - 대응: 여러 뉴스 소스 활용, 크롤링 대안 검토

3. **이메일 전송 실패**
   - 대응: 재시도 로직, 에러 로깅, 대체 이메일 서비스

4. **데이터베이스 성능**
   - 대응: 인덱스 최적화, 쿼리 최적화, 연결 풀 설정

### 일정 리스크

1. **개발 지연**
   - 대응: MVP 기능 우선, 선택 기능 제외

2. **배포 문제**
   - 대응: 로컬 테스트 강화, 스테이징 환경 활용

---

## 추가 개선 사항 (MVP 이후)

### 기능 개선
- [ ] 사용자 대시보드
- [ ] 보고서 즐겨찾기
- [ ] 알림 설정
- [ ] 보고서 검색 기능
- [ ] 과거 보고서 아카이브

### 기술 개선
- [ ] 캐싱 전략 (Redis)
- [ ] 백그라운드 작업 큐 (Celery)
- [ ] 로깅 및 모니터링
- [ ] API Rate Limiting
- [ ] 인증/인가 시스템

### UX 개선
- [ ] 다크 모드
- [ ] 애니메이션 효과
- [ ] 차트/그래프 시각화
- [ ] 소셜 공유 기능

---

## 참고 자료

### 문서
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Next.js 15 공식 문서](https://nextjs.org/docs)
- [OpenAI API 문서](https://platform.openai.com/docs)
- [PostgreSQL 문서](https://www.postgresql.org/docs/)

### 도구
- [Vercel 배포 가이드](https://vercel.com/docs)
- [Railway 배포 가이드](https://docs.railway.app/)
- [Docker Compose 문서](https://docs.docker.com/compose/)

---

**작성일**: 2024-01-15  
**버전**: 1.0  
**상태**: 초안
