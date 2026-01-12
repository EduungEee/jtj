# 📈 뉴스 기반 주식 동향 분석 서비스 [market-report.today](http://market-report.today)

뉴스 데이터를 분석하여 유망 산업을 파악하고, 분석 결과를 보고서로 제공하는 서비스입니다.

## 🎯 프로젝트 개요

최신 뉴스를 수집하고 AI를 활용하여 주식 시장 동향을 분석합니다. 단순히 뉴스 내용을 파악하는 것을 넘어, 각 뉴스 기사로 인한 **사회적 파급효과**를 예측하고, 그로 인해 영향을 받는 **산업과 주식**을 분석합니다. 분석 결과를 웹 보고서로 생성하고, 사용자에게 이메일로 전송합니다. 사용자는 이메일 링크를 통해 상세한 분석 보고서를 확인할 수 있습니다.

## ✨ 주요 기능

- 🏠 **홈페이지**:
  - 가입 유도 섹션
  - 오늘 작성된 보고서 미리보기 및 클릭 시 보고서 페이지로 이동
  - 분석 방식 및 서비스 소개 홍보 섹션
- 📰 **뉴스 수집**: 최신 뉴스 데이터 자동 수집
- 🤖 **AI 분석**:
  - 뉴스 기사 내용 분석
  - 기사로 인한 사회적 파급효과 예측
  - 파급효과에 따른 영향받는 산업 및 주식 분석
- 📊 **보고서 생성**: 분석 결과를 웹 보고서 페이지로 생성
- 📧 **이메일 전송**: 생성된 보고서 링크를 사용자 이메일로 전송
- 🔗 **보고서 조회**: 이메일 링크를 통해 보고서 페이지 접근

## 🛠 기술 스택 (MVP)

- **Backend**: FastAPI, PostgreSQL, OpenAI API
- **Frontend**: Next.js 15 (App Router)
- **기타**: Docker Compose, 네이버 뉴스 API, SendGrid/Resend (이메일 API)

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
```

## 📝 API 엔드포인트

- `GET /api/reports/today` - 오늘의 보고서 목록
- `GET /api/report/{report_id}` - 보고서 상세
- `POST /api/analyze` - 뉴스 분석 요청
- `POST /api/subscribe` - 이메일 구독

## 🔧 환경 변수

```env
OPENAI_API_KEY=your_openai_api_key
# 네이버 뉴스 API
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
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
