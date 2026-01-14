# 배포 가이드

이 문서는 뉴스 기반 주식 동향 분석 서비스를 AWS EC2와 Vercel에 배포하는 방법을 설명합니다.

## 배포 아키텍처

```
┌─────────────────┐         ┌──────────────────┐
│   Vercel        │         │   AWS EC2        │
│  (Frontend)     │────────▶│  Ubuntu Server   │
│                 │  HTTP   │                  │
│  Next.js 15     │         │  nginx:80        │
│                 │         │    ↓             │
│  *.vercel.app   │         │  FastAPI:8000    │
└─────────────────┘         │  PostgreSQL:5432 │
                            └──────────────────┘
```

## 목차

1. [AWS EC2 인스턴스 생성](#1-aws-ec2-인스턴스-생성)
2. [EC2 서버 초기 설정](#2-ec2-서버-초기-설정)
3. [백엔드 배포](#3-백엔드-배포)
4. [nginx 설정](#4-nginx-설정)
5. [프론트엔드 배포 (Vercel)](#5-프론트엔드-배포-vercel)
6. [서비스 자동 시작 설정](#6-서비스-자동-시작-설정)
7. [트러블슈팅](#7-트러블슈팅)
8. [모니터링 및 유지보수](#8-모니터링-및-유지보수)

---

## 1. AWS EC2 인스턴스 생성

### 1.1 EC2 인스턴스 생성

1. AWS 콘솔에 로그인하고 EC2 서비스로 이동
2. "인스턴스 시작" 클릭
3. 다음 설정을 선택:
   - **이름**: `stock-analysis-backend` (또는 원하는 이름)
   - **AMI**: Ubuntu Server 22.04 LTS (HVM) - SSD Volume Type
   - **인스턴스 타입**:
     - 개발/테스트: `t3.micro` (프리티어)
     - 프로덕션: `t3.small` 또는 `t3.medium` (권장)
   - **키 페어**: 새 키 페어 생성 또는 기존 키 페어 선택
     - 키 페어 이름 입력 (예: `stock-analysis-key`)
     - 키 페어 다운로드 (`.pem` 파일)
     - **중요**: 키 페어 파일을 안전한 곳에 보관

### 1.2 보안 그룹 설정

네트워크 설정에서 보안 그룹을 생성하거나 기존 그룹을 편집합니다:

**인바운드 규칙:**

- **SSH (22)**: 소스 `내 IP` 또는 `0.0.0.0/0` (보안상 특정 IP로 제한 권장)
- **HTTP (80)**: 소스 `0.0.0.0/0`

**아웃바운드 규칙:**

- 모든 트래픽 허용 (기본값)

### 1.3 Elastic IP 할당 (선택사항)

고정 IP 주소가 필요한 경우:

1. EC2 콘솔에서 "탄력적 IP" 메뉴로 이동
2. "탄력적 IP 주소 할당" 클릭
3. 할당된 IP를 생성한 EC2 인스턴스에 연결

### 1.4 EC2 인스턴스 접속

다운로드한 키 페어 파일의 권한을 설정하고 SSH로 접속:

```bash
# 키 페어 파일 권한 설정 (Mac/Linux)
chmod 400 ~/Downloads/stock-analysis-key.pem

# EC2 인스턴스 접속
ssh -i ~/Downloads/stock-analysis-key.pem ubuntu@<EC2_PUBLIC_IP>
```

Windows의 경우 PuTTY나 WSL을 사용할 수 있습니다.

---

## 2. EC2 서버 초기 설정

### 2.1 시스템 업데이트

```bash
sudo apt update
sudo apt upgrade -y
```

### 2.2 Docker 설치

```bash
# Docker 설치 스크립트 다운로드 및 실행
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 설치 확인
docker --version
```

**중요**: docker 그룹에 추가한 후에는 로그아웃 후 다시 로그인하거나 다음 명령어를 실행해야 합니다:

```bash
newgrp docker
```

### 2.3 Docker Compose 설치

```bash
# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 설치 확인
docker-compose --version
# 또는 (최신 버전)
docker compose version
```

### 2.4 nginx 설치

```bash
sudo apt install nginx -y

# nginx 시작 및 자동 시작 설정
sudo systemctl start nginx
sudo systemctl enable nginx

# 상태 확인
sudo systemctl status nginx
```

### 2.5 방화벽 설정 (UFW)

```bash
# UFW 활성화
sudo ufw enable

# 필요한 포트 열기
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP

# 상태 확인
sudo ufw status
```

**참고**: AWS 보안 그룹에서도 포트를 열어야 합니다. UFW와 보안 그룹 모두 설정해야 합니다.

---

## 3. 백엔드 배포

### 3.1 프로젝트 파일 업로드

프로젝트 파일을 EC2 서버에 업로드하는 방법:

#### Git을 사용한 클론 (권장)

```bash
# Git 설치 (아직 설치되지 않은 경우)
sudo apt install git -y

# 프로젝트 클론
cd ~
git clone <your-repository-url> stock-analysis
cd stock-analysis
```

### 3.2 환경 변수 설정

EC2 서버에서 `.env` 파일을 생성합니다:

```bash
cd ~/stock-analysis

# .env 파일 생성
nano .env
```

다음 내용을 입력합니다:

```env
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# NewsData.io API Key
NEWSDATA_API_KEY=your_newsdata_api_key_here

# Database URL (docker-compose 사용 시 자동 설정됨)
# DATABASE_URL=postgresql://postgres:postgres@postgres:5432/stock_analysis

# 프론트엔드 URL (CORS 설정용)
FRONTEND_URL=https://your-frontend-domain.vercel.app

# Vercel 도메인 목록 (쉼표로 구분, 여러 도메인 허용)
# 예: VERCEL_DOMAINS=https://your-app.vercel.app,https://www.yourdomain.com
VERCEL_DOMAINS=https://your-app.vercel.app

# 환경 설정
ENVIRONMENT=production
```

파일 저장: `Ctrl + O`, `Enter`, `Ctrl + X`

### 3.3 배포 스크립트 실행

```bash
# 배포 스크립트에 실행 권한 부여
chmod +x deploy/ec2-deploy.sh

# 배포 스크립트 실행
./deploy/ec2-deploy.sh
```

또는 수동으로 실행:

```bash
# Docker 이미지 빌드
docker-compose -f docker-compose.prod.yml build --no-cache

# 컨테이너 시작
docker-compose -f docker-compose.prod.yml up -d

# 서비스 상태 확인
docker-compose -f docker-compose.prod.yml ps

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f backend
```

### 3.4 서비스 상태 확인

```bash
# 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml ps

# 백엔드 로그 확인
docker-compose -f docker-compose.prod.yml logs backend

# 데이터베이스 연결 확인
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.database import engine; print('DB 연결 성공' if engine else 'DB 연결 실패')"
```

### 3.5 백엔드 API 테스트

로컬 컴퓨터에서 테스트:

```bash
# 헬스 체크
curl http://<EC2_PUBLIC_IP>:8000/api/health

# API 문서 확인 (nginx 설정 전)
curl http://<EC2_PUBLIC_IP>:8000/docs
```

---

## 4. nginx 설정

### 4.1 nginx 설정 파일 복사

```bash
# nginx 설정 파일 복사
sudo cp ~/jtj/nginx/nginx.conf /etc/nginx/sites-available/jtj

# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/jtj /etc/nginx/sites-enabled/

# 기본 설정 비활성화 (선택사항)
sudo rm /etc/nginx/sites-enabled/default

# nginx 설정 테스트
sudo nginx -t

# nginx 재시작
sudo systemctl restart nginx
```

### 4.2 HTTP 접근 확인

```bash
# HTTP로 API 접근 테스트
curl http://<EC2_PUBLIC_IP>/api/health
```

---

## 5. 프론트엔드 배포 (Vercel)

### 5.1 Vercel 프로젝트 생성

1. [Vercel](https://vercel.com)에 로그인
2. "Add New Project" 클릭
3. GitHub 저장소를 연결하거나 직접 배포

### 5.2 환경 변수 설정

Vercel 대시보드에서 프로젝트 설정 > Environment Variables로 이동하여 다음 변수를 추가:

- **NEXT_PUBLIC_API_URL**: `http://<EC2_PUBLIC_IP>`

**참고**: Vercel 배포 후 실제 도메인을 확인하여 백엔드의 `.env` 파일에 `VERCEL_DOMAINS` 환경 변수를 추가해야 합니다.

### 5.3 빌드 설정

Vercel은 `vercel.json` 파일을 자동으로 인식합니다. 프로젝트 루트가 아닌 `frontend` 디렉토리를 루트로 설정해야 할 수 있습니다:

1. Vercel 프로젝트 설정에서 "Root Directory"를 `frontend`로 설정
2. 또는 `vercel.json`에서 빌드 명령어가 올바르게 설정되어 있는지 확인

### 5.4 배포 실행

1. GitHub에 코드를 푸시하면 자동으로 배포됩니다
2. 또는 Vercel 대시보드에서 "Deploy" 버튼을 클릭

### 5.5 커스텀 도메인 설정 (선택사항)

1. Vercel 프로젝트 설정 > Domains로 이동
2. 도메인 추가
3. DNS 설정 안내에 따라 도메인을 설정

---

## 6. 서비스 자동 시작 설정

### 6.1 docker-compose 자동 시작 설정

systemd 서비스 파일을 생성합니다:

```bash
sudo nano /etc/systemd/system/stock-analysis.service
```

다음 내용을 입력:

```ini
[Unit]
Description=Stock Analysis Backend Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/stock-analysis
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target
```

서비스 활성화:

```bash
# systemd 데몬 재로드
sudo systemctl daemon-reload

# 서비스 활성화
sudo systemctl enable stock-analysis.service

# 서비스 시작
sudo systemctl start stock-analysis.service

# 서비스 상태 확인
sudo systemctl status stock-analysis.service
```

### 6.2 nginx 자동 시작 확인

nginx는 기본적으로 자동 시작이 설정되어 있습니다:

```bash
# 자동 시작 확인
sudo systemctl is-enabled nginx

# 자동 시작 설정 (필요한 경우)
sudo systemctl enable nginx
```

---

## 7. 트러블슈팅

### 7.1 보안 그룹 설정 문제

**문제**: HTTP 접근이 안 됩니다.

**해결 방법**:

- AWS 콘솔에서 보안 그룹 인바운드 규칙 확인
- 포트 80이 열려있는지 확인
- 소스가 `0.0.0.0/0`으로 설정되어 있는지 확인

### 7.2 포트 접근 불가

**문제**: 특정 포트로 접근이 안 됩니다.

**해결 방법**:

```bash
# UFW 상태 확인
sudo ufw status

# 포트 열기
sudo ufw allow <PORT>/tcp

# AWS 보안 그룹도 확인
```

### 7.3 Docker 컨테이너 실행 오류

**문제**: 컨테이너가 시작되지 않습니다.

**해결 방법**:

```bash
# 로그 확인
docker-compose -f docker-compose.prod.yml logs

# 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml ps

# 컨테이너 재시작
docker-compose -f docker-compose.prod.yml restart

# 완전히 재시작
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### 7.4 데이터베이스 연결 오류

**문제**: 백엔드가 데이터베이스에 연결하지 못합니다.

**해결 방법**:

```bash
# PostgreSQL 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml ps postgres

# PostgreSQL 로그 확인
docker-compose -f docker-compose.prod.yml logs postgres

# .env 파일의 DATABASE_URL 확인
cat .env | grep DATABASE_URL
```

### 7.5 nginx 설정 오류

**문제**: nginx가 시작되지 않습니다.

**해결 방법**:

```bash
# nginx 설정 테스트
sudo nginx -t

# nginx 로그 확인
sudo tail -f /var/log/nginx/error.log

# nginx 상태 확인
sudo systemctl status nginx
```

### 7.6 CORS 오류

**문제**: 프론트엔드에서 API 호출 시 CORS 오류가 발생합니다.

**해결 방법**:

1. `backend/app/main.py`의 CORS 설정 확인
2. Vercel 도메인이 `allow_origins`에 포함되어 있는지 확인
3. nginx의 CORS 헤더 설정 확인

---

## 8. 모니터링 및 유지보수

### 8.1 로그 모니터링

```bash
# 백엔드 로그 실시간 확인
docker-compose -f docker-compose.prod.yml logs -f backend

# PostgreSQL 로그 확인
docker-compose -f docker-compose.prod.yml logs -f postgres

# nginx 액세스 로그
sudo tail -f /var/log/nginx/access.log

# nginx 에러 로그
sudo tail -f /var/log/nginx/error.log
```

### 8.2 백업 전략

#### 데이터베이스 백업

```bash
# PostgreSQL 백업
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres stock_analysis > backup_$(date +%Y%m%d).sql

# 백업 복원
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres stock_analysis < backup_20240101.sql
```

#### 자동 백업 스크립트

`deploy/backup.sh` 파일 생성:

```bash
#!/bin/bash
BACKUP_DIR=~/backups
mkdir -p $BACKUP_DIR
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres stock_analysis > $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql
# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

crontab에 추가:

```bash
crontab -e
# 매일 새벽 2시에 백업
0 2 * * * /home/ubuntu/stock-analysis/deploy/backup.sh
```

### 8.3 업데이트 방법

```bash
# 프로젝트 디렉토리로 이동
cd ~/stock-analysis

# 최신 코드 가져오기 (Git 사용 시)
git pull origin main

# 환경 변수 확인
# .env 파일이 변경되었는지 확인하고 필요시 업데이트

# Docker 이미지 재빌드
docker-compose -f docker-compose.prod.yml build --no-cache

# 컨테이너 재시작
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# 서비스 상태 확인
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f backend
```

### 8.4 리소스 모니터링

```bash
# 디스크 사용량 확인
df -h

# 메모리 사용량 확인
free -h

# Docker 컨테이너 리소스 사용량
docker stats

# 시스템 로그 확인
sudo journalctl -u stock-analysis.service -f
```

### 8.5 비용 최적화

- **인스턴스 타입**: 사용량에 맞는 인스턴스 타입 선택
- **Elastic IP**: 사용하지 않으면 비용이 발생하므로 필요시만 사용
- **스냅샷**: 불필요한 스냅샷 정리
- **모니터링**: CloudWatch를 사용하여 리소스 사용량 모니터링

---

## 추가 리소스

- [AWS EC2 문서](https://docs.aws.amazon.com/ec2/)
- [Docker 문서](https://docs.docker.com/)
- [nginx 문서](https://nginx.org/en/docs/)
- [Vercel 문서](https://vercel.com/docs)

---

## 지원

문제가 발생하거나 도움이 필요한 경우:

1. 로그를 확인하여 오류 메시지 확인
2. 트러블슈팅 섹션 참조
3. GitHub Issues에 문제 보고
