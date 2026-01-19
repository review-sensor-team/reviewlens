#!/bin/bash
# PostgreSQL 및 데이터베이스 환경 시작

set -e

echo "========================================="
echo "PostgreSQL 데이터베이스 시작"
echo "========================================="

# DB 컨테이너 시작
echo "📦 PostgreSQL 컨테이너 시작 중..."
docker-compose -f docker-compose.db.yml up -d

# DB 준비 대기
echo "⏳ PostgreSQL 준비 대기 중..."
sleep 5

# 헬스체크
echo "🔍 PostgreSQL 연결 확인..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker exec reviewlens-postgres pg_isready -U reviewlens -d reviewlens > /dev/null 2>&1; then
        echo "✅ PostgreSQL 준비 완료"
        break
    fi
    
    attempt=$((attempt + 1))
    echo "   시도 $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ PostgreSQL 연결 실패"
    exit 1
fi

# 스키마 확인
echo ""
echo "🔍 데이터베이스 스키마 확인..."
docker exec reviewlens-postgres psql -U reviewlens -d reviewlens -c "\dt" || true

echo ""
echo "========================================="
echo "✅ PostgreSQL 시작 완료"
echo "========================================="
echo ""
echo "📊 접속 정보:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Database: reviewlens"
echo "  - User: reviewlens"
echo "  - Password: reviewlens_dev_password"
echo ""
echo "  - pgAdmin: http://localhost:5050"
echo "    Email: admin@reviewlens.local"
echo "    Password: admin"
echo ""
echo "📝 연결 테스트:"
echo "  psql -h localhost -U reviewlens -d reviewlens"
echo ""
echo "🛑 종료:"
echo "  ./db_stop.sh"
echo ""
