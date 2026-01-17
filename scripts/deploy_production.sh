#!/bin/bash
# ReviewLens 프로덕션 배포 스크립트 (Docker Compose)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 ReviewLens 프로덕션 배포 시작..."

# 환경 확인
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "❌ .env 파일이 없습니다. .env.example을 복사하여 설정하세요."
    exit 1
fi

# Docker 확인
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되지 않았습니다."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose가 설치되지 않았습니다."
    exit 1
fi

# 1. 기존 컨테이너 중지
echo "📦 기존 모니터링 컨테이너 중지 중..."
docker-compose -f "$PROJECT_ROOT/docker-compose.monitoring.yml" down || true

# 2. 모니터링 스택 시작
echo "📊 모니터링 스택 시작 중..."
cd "$PROJECT_ROOT"
docker-compose -f docker-compose.monitoring.yml up -d

# 헬스 체크
echo "⏳ 컨테이너 헬스 체크 중..."
sleep 5

if docker ps | grep -q reviewlens_prometheus; then
    echo "✅ Prometheus 실행 중"
else
    echo "❌ Prometheus 시작 실패"
    docker-compose -f docker-compose.monitoring.yml logs prometheus
    exit 1
fi

if docker ps | grep -q reviewlens_grafana; then
    echo "✅ Grafana 실행 중"
else
    echo "❌ Grafana 시작 실패"
    docker-compose -f docker-compose.monitoring.yml logs grafana
    exit 1
fi

# 3. 백엔드 서비스 재시작 (systemd 사용 시)
if systemctl is-active --quiet reviewlens-api; then
    echo "🔄 API 서버 재시작 중..."
    sudo systemctl restart reviewlens-api
    echo "✅ API 서버 재시작 완료"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 프로덕션 배포 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 모니터링:"
echo "  - Prometheus: http://$(hostname -I | awk '{print $1}'):9090"
echo "  - Grafana:    http://$(hostname -I | awk '{print $1}'):3001"
echo ""
echo "📋 상태 확인:"
echo "  docker-compose -f docker-compose.monitoring.yml ps"
echo "  systemctl status reviewlens-api"
echo ""
echo "📁 로그:"
echo "  docker-compose -f docker-compose.monitoring.yml logs -f"
echo "  journalctl -u reviewlens-api -f"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
