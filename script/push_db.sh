#!/bin/bash

# 로컬 DB를 덤프해서 원격 DB로 복원하는 스크립트
# 사용법: ./push_db.sh [--overwrite|--append]

set -e

# 원격 DB 설정 (대화형 입력)
REMOTE_DB="stock_analysis"
REMOTE_USER="postgres"

# 로컬 DB 설정 (docker-compose 사용)
LOCAL_DB="stock_analysis"
LOCAL_USER="postgres"
LOCAL_PASSWORD="postgres"
DOCKER_COMPOSE_FILE="docker-compose.yml"

# 덤프 파일 저장 경로
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="${BACKUP_DIR}/local_dump_${TIMESTAMP}.sql"

# 원격 DB 정보 입력 (보안을 위해 대화형 입력)
echo "=========================================="
echo "원격 DB 정보 입력"
echo "=========================================="
read -p "원격 DB 호스트 IP 주소: " REMOTE_HOST
if [ -z "${REMOTE_HOST}" ]; then
    echo "❌ 호스트 IP 주소는 필수입니다."
    exit 1
fi

read -sp "원격 DB 비밀번호: " REMOTE_PASSWORD
echo ""
if [ -z "${REMOTE_PASSWORD}" ]; then
    echo "❌ 비밀번호는 필수입니다."
    exit 1
fi

# 옵션 파싱
if [ "$1" == "--append" ]; then
    MODE="append"
elif [ "$1" == "--overwrite" ]; then
    MODE="overwrite"
elif [ -z "$1" ]; then
    # 옵션이 없으면 대화형으로 선택
    echo ""
    echo "=========================================="
    echo "복원 모드를 선택하세요:"
    echo "=========================================="
    echo "1) 덮어쓰기 (기존 원격 DB를 완전히 교체) ⚠️  위험!"
    echo "2) 추가 (기존 원격 DB에 데이터 추가)"
    echo "=========================================="
    read -p "선택 (1 또는 2): " choice
    
    case "$choice" in
        1)
            MODE="overwrite"
            ;;
        2)
            MODE="append"
            ;;
        *)
            echo "❌ 잘못된 선택입니다. 1 또는 2를 입력하세요."
            exit 1
            ;;
    esac
else
    echo "사용법: $0 [--overwrite|--append]"
    echo "  --overwrite: 원격 DB를 완전히 덮어씁니다"
    echo "  --append: 원격 DB에 데이터를 추가합니다"
    echo ""
    echo "옵션 없이 실행하면 대화형 메뉴가 표시됩니다."
    exit 1
fi

# 백업 디렉토리 생성
mkdir -p "${BACKUP_DIR}"

echo "=========================================="
echo "로컬 DB에서 원격 DB로 데이터 푸시하기"
echo "=========================================="
echo "로컬: docker-compose postgres/${LOCAL_DB}"
echo "원격: ${REMOTE_HOST}/${REMOTE_DB}"
echo "모드: ${MODE}"
echo "=========================================="
echo ""

# 1. 로컬 DB에서 덤프 생성
echo "📥 로컬 DB에서 덤프 생성 중..."

# docker-compose가 실행 중인지 확인
if ! docker-compose -f "${DOCKER_COMPOSE_FILE}" ps postgres | grep -q "Up"; then
    echo "❌ docker-compose의 postgres 컨테이너가 실행 중이 아닙니다."
    echo "   docker-compose up -d를 실행하세요."
    exit 1
fi

# docker-compose를 통해 덤프 생성 (버전 불일치 문제 해결)
docker-compose -f "${DOCKER_COMPOSE_FILE}" exec -T postgres \
    pg_dump -U "${LOCAL_USER}" -d "${LOCAL_DB}" --no-owner --no-acl \
    > "${DUMP_FILE}"

if [ $? -ne 0 ]; then
    echo "❌ 덤프 생성 실패"
    exit 1
fi

echo "✅ 덤프 생성 완료: ${DUMP_FILE}"
echo ""

# 2. 원격 DB 복원
if [ "${MODE}" == "overwrite" ]; then
    echo "🔄 덮어쓰기 모드: 원격 데이터베이스를 삭제하고 복원합니다..."
    echo "⚠️  경고: 원격 DB의 모든 데이터가 삭제됩니다!"
    read -p "계속하시겠습니까? (yes/no): " confirm
    
    if [ "${confirm}" != "yes" ]; then
        echo "❌ 취소되었습니다."
        exit 1
    fi
    
    # 기존 데이터베이스에 연결된 모든 세션 종료
    echo "🔌 기존 연결 종료 중..."
    PGPASSWORD="${REMOTE_PASSWORD}" psql \
        -h "${REMOTE_HOST}" \
        -U "${REMOTE_USER}" \
        -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${REMOTE_DB}' AND pid <> pg_backend_pid();" \
        > /dev/null 2>&1 || true
    
    # 잠시 대기 (연결 종료 시간 확보)
    sleep 1
    
    # 기존 데이터베이스 삭제 및 재생성
    echo "🗑️  원격 데이터베이스 삭제 중..."
    PGPASSWORD="${REMOTE_PASSWORD}" psql \
        -h "${REMOTE_HOST}" \
        -U "${REMOTE_USER}" \
        -d postgres \
        -c "DROP DATABASE IF EXISTS ${REMOTE_DB};"
    
    echo "🆕 새 데이터베이스 생성 중..."
    PGPASSWORD="${REMOTE_PASSWORD}" psql \
        -h "${REMOTE_HOST}" \
        -U "${REMOTE_USER}" \
        -d postgres \
        -c "CREATE DATABASE ${REMOTE_DB};"
    
    # 덤프 복원
    echo "📤 덤프 복원 중..."
    PGPASSWORD="${REMOTE_PASSWORD}" psql \
        -h "${REMOTE_HOST}" \
        -U "${REMOTE_USER}" \
        -d "${REMOTE_DB}" \
        < "${DUMP_FILE}"
    
    if [ $? -ne 0 ]; then
        echo "❌ 복원 실패"
        exit 1
    fi
    
    echo "✅ 덮어쓰기 완료!"
    
elif [ "${MODE}" == "append" ]; then
    echo "➕ 추가 모드: 원격 DB에 데이터를 추가합니다..."
    
    # 원격 DB 연결 확인
    if ! PGPASSWORD="${REMOTE_PASSWORD}" psql -h "${REMOTE_HOST}" -U "${REMOTE_USER}" -d "${REMOTE_DB}" -c "SELECT 1" > /dev/null 2>&1; then
        echo "❌ 원격 PostgreSQL에 연결할 수 없습니다."
        echo "   네트워크 연결 및 보안 그룹 설정을 확인하세요."
        exit 1
    fi
    
    # 덤프 복원 (기존 데이터 유지)
    echo "📤 덤프 복원 중 (기존 데이터 유지)..."
    PGPASSWORD="${REMOTE_PASSWORD}" psql \
        -h "${REMOTE_HOST}" \
        -U "${REMOTE_USER}" \
        -d "${REMOTE_DB}" \
        < "${DUMP_FILE}" 2>&1 | grep -v "already exists" || true
    
    echo "✅ 추가 완료!"
fi

echo ""
echo "=========================================="
echo "✅ 완료!"
echo "덤프 파일: ${DUMP_FILE}"
echo "=========================================="
