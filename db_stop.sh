#!/bin/bash
# PostgreSQL 데이터베이스 종료

set -e

echo "========================================="
echo "PostgreSQL 데이터베이스 종료"
echo "========================================="

# DB 컨테이너 종료
echo "🛑 PostgreSQL 컨테이너 종료 중..."
docker-compose -f docker-compose.db.yml down

echo ""
echo "✅ PostgreSQL 종료 완료"
echo ""
