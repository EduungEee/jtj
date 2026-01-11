# 📈 뉴스 기반 주식 동향 분석 서비스

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

### Backend

- **Python** - FastAPI
- **AI/ML**: OpenAI API
- **데이터베이스**: PostgreSQL
- **이메일**: SMTP 또는 SendGrid API

### Frontend

- **Next.js 15** - App Router 기반 보고서 페이지

### 기타

- **뉴스 API**: NewsAPI 또는 네이버/다음 뉴스 API
- **컨테이너화**: Docker & Docker Compose
- **배포**:
  - Frontend: Vercel
  - Backend: Railway (PostgreSQL 포함)

## 📁 프로젝트 구조

```
jtj/
├── backend/          # 백엔드 서버
│   ├── app/
│   │   ├── main.py   # FastAPI 메인
│   │   ├── news.py   # 뉴스 수집 모듈
│   │   ├── analysis.py  # AI 분석 모듈
│   │   ├── report.py    # 보고서 생성 모듈
│   │   └── email.py     # 이메일 전송 모듈
│   ├── models/       # 데이터베이스 모델
│   ├── Dockerfile    # Backend Docker 이미지
│   └── requirements.txt
├── frontend/         # 프론트엔드 (Next.js 15)
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx  # 홈페이지
│   │   └── report/
│   │       └── [id]/
│   │           └── page.tsx  # 보고서 페이지
│   ├── Dockerfile    # Frontend Docker 이미지
│   └── package.json
├── docker-compose.yml  # 로컬 개발 환경 설정
├── .env.example
└── README.md
```

## 🚀 빠른 시작

### Docker Compose를 사용한 방법 (권장)

#### 1. 저장소 클론

```bash
git clone <repository-url>
cd jtj
```

#### 2. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에 API 키 등 설정
```

#### 3. Docker Compose로 전체 서비스 실행

```bash
docker-compose up -d
```

이 명령어로 다음 서비스들이 자동으로 실행됩니다:

- PostgreSQL 데이터베이스 (포트 5432)
- FastAPI 백엔드 (포트 8000)
- Next.js 프론트엔드 (포트 3000)

#### 4. 서비스 확인

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API 문서: http://localhost:8000/docs

#### 5. 로그 확인

```bash
docker-compose logs -f
```

#### 6. 서비스 중지

```bash
docker-compose down
```

### 수동 설정 방법

#### 1. 저장소 클론

```bash
git clone <repository-url>
cd jtj
```

#### 2. PostgreSQL 설정

PostgreSQL이 설치되어 있어야 합니다. Docker로 실행하려면:

```bash
docker run --name postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=stock_analysis -p 5432:5432 -d postgres:15
```

#### 3. Backend 설정

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 4. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에 API 키 및 PostgreSQL 연결 정보 설정
```

#### 5. Backend 실행

```bash
python app/main.py
```

#### 6. Frontend 설정 및 실행

```bash
cd frontend
npm install
npm run dev
# Next.js 15가 http://localhost:3000 에서 실행됩니다
```

## 📝 API 엔드포인트

- `GET /api/reports/today` - 오늘 작성된 보고서 목록 조회 (홈페이지용)
- `POST /api/analyze` - 뉴스 분석 요청
- `GET /api/report/{report_id}` - 보고서 조회
- `POST /api/send-email` - 이메일 전송

## 🔧 환경 변수

```env
# AI API
OPENAI_API_KEY=your_openai_api_key

# 뉴스 API
NEWS_API_KEY=your_news_api_key

# 이메일
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_password

# PostgreSQL 데이터베이스
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=stock_analysis
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/stock_analysis

# Backend
BACKEND_URL=http://localhost:8000

# Frontend URL (이메일 링크용)
FRONTEND_URL=http://localhost:3000
```

### Docker Compose 환경 변수

`docker-compose.yml`에서 사용하는 환경 변수는 `.env` 파일에서 자동으로 로드됩니다.

## 🏠 홈페이지 구성

홈페이지는 다음 3가지 주요 섹션으로 구성됩니다:

1. **가입 유도 섹션**

   - 서비스의 가치 제안 및 혜택 소개
   - 이메일 가입 CTA (Call To Action)

2. **오늘의 보고서 미리보기**

   - 오늘 작성된 보고서 목록 표시
   - 각 보고서의 요약 정보 (제목, 주요 산업, 생성 시간 등)
   - 클릭 시 해당 보고서 상세 페이지로 이동

3. **분석 방식 소개**
   - 뉴스 기사 분석 프로세스 설명
   - 사회적 파급효과 예측 방법론
   - 산업 및 주식 영향 분석 과정
   - 서비스의 차별점 및 신뢰성 강조

## 🐳 Docker Compose 설정

프로젝트 루트에 `docker-compose.yml` 파일이 포함되어 있습니다. 이 파일은 다음 서비스를 정의합니다:

- **postgres**: PostgreSQL 15 데이터베이스
- **backend**: FastAPI 백엔드 서버
- **frontend**: Next.js 15 프론트엔드 서버

### Docker Compose 파일 구조

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: stock_analysis
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/stock_analysis
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend

volumes:
  postgres_data:
```

## 📊 보고서 예시

보고서에는 다음 정보가 포함됩니다:

- 분석된 뉴스 기사 요약
- 각 기사로 인한 예상 사회적 파급효과
- 파급효과에 따라 영향받는 산업 목록
- 영향받는 산업별 관련 주식 및 예상 동향
- 투자 인사이트 및 추천

## 🚢 배포

### Frontend (Vercel)

1. Vercel에 프로젝트 연결
2. 환경 변수 설정:
   - `NEXT_PUBLIC_API_URL`: 배포된 백엔드 URL

### Backend & Database (Railway)

1. Railway에 프로젝트 연결
2. PostgreSQL 서비스 추가
3. 환경 변수 설정:
   - `DATABASE_URL`: Railway가 자동으로 제공하는 PostgreSQL 연결 문자열
   - `OPENAI_API_KEY`: OpenAI API 키
   - `NEWS_API_KEY`: 뉴스 API 키
   - `SMTP_*`: 이메일 설정
   - `FRONTEND_URL`: 배포된 프론트엔드 URL

### 배포 후 확인사항

- Frontend에서 Backend API 연결 확인
- 데이터베이스 마이그레이션 실행
- 이메일 전송 기능 테스트

## 🤝 기여하기

해커톤 프로젝트이므로 자유롭게 기여해주세요!

## 📄 라이선스

MIT License

## 👥 팀

- [팀원 이름들]

---

**해커톤 MVP 버전** - 빠른 프로토타이핑을 위한 최소 기능 구현
