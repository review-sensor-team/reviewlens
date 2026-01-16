#!/bin/bash

# ReviewLens 모니터링 시스템 재시작 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ReviewLens 모니터링 시스템 재시작                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. 기존 프로세스 중지
echo "🔄 Step 1: 기존 모니터링 프로세스 중지"
bash "$SCRIPT_DIR/monitor_stop.sh"

echo ""
echo "⏳ 프로세스 종료 대기 중... (3초)"
sleep 3

# 2. Prometheus & Grafana 설치 확인
echo ""
echo "🔄 Step 2: Prometheus & Grafana 설치 확인"

if ! command -v prometheus &> /dev/null; then
    echo "   ⚠️  Prometheus가 설치되어 있지 않습니다"
    echo "   📦 Homebrew로 설치 중..."
    brew install prometheus
fi

if ! command -v grafana &> /dev/null; then
    echo "   ⚠️  Grafana가 설치되어 있지 않습니다"
    echo "   📦 Homebrew로 설치 중..."
    brew install grafana
fi

echo "   ✓ Prometheus: $(which prometheus)"
echo "   ✓ Grafana: $(which grafana)"

# 3. 설정 파일 확인 및 업데이트
echo ""
echo "🔄 Step 3: 설정 파일 업데이트"

# Prometheus 설정
if [ -f "$PROJECT_ROOT/monitoring/prometheus.yml" ]; then
    echo "   📝 Prometheus 설정 복사 중..."
    cp "$PROJECT_ROOT/monitoring/prometheus.yml" /opt/homebrew/etc/prometheus.yml
    echo "   ✓ /opt/homebrew/etc/prometheus.yml"
else
    echo "   ⚠️  monitoring/prometheus.yml 파일을 찾을 수 없습니다"
fi

# Grafana 포트 설정 확인
echo "   📝 Grafana 포트 확인 중..."
if grep -q "^http_port = 3001" /opt/homebrew/etc/grafana/grafana.ini; then
    echo "   ✓ Grafana 포트: 3001 (설정됨)"
else
    echo "   ⚙️  Grafana 포트를 3001로 설정 중..."
    if grep -q "^;http_port = 3000" /opt/homebrew/etc/grafana/grafana.ini; then
        sed -i '' 's/^;http_port = 3000/http_port = 3001/' /opt/homebrew/etc/grafana/grafana.ini
    elif grep -q "^http_port = 3000" /opt/homebrew/etc/grafana/grafana.ini; then
        sed -i '' 's/^http_port = 3000/http_port = 3001/' /opt/homebrew/etc/grafana/grafana.ini
    else
        echo "http_port = 3001" >> /opt/homebrew/etc/grafana/grafana.ini
    fi
    echo "   ✓ Grafana 포트: 3001 (변경됨)"
fi

# 4. 로그 디렉토리 생성
mkdir -p /tmp/reviewlens-monitoring

# 5. Prometheus 시작
echo ""
echo "🔄 Step 4: Prometheus 시작"
nohup prometheus \
    --config.file=/opt/homebrew/etc/prometheus.yml \
    --storage.tsdb.path=/opt/homebrew/var/prometheus \
    > /tmp/reviewlens-monitoring/prometheus.log 2>&1 &

PROM_PID=$!
echo "   ✓ Prometheus 시작됨 (PID: $PROM_PID)"
echo "   📝 로그: /tmp/reviewlens-monitoring/prometheus.log"

# 6. Grafana 시작
echo ""
echo "🔄 Step 5: Grafana 시작"
nohup grafana server \
    --config /opt/homebrew/etc/grafana/grafana.ini \
    --homepath /opt/homebrew/opt/grafana/share/grafana \
    > /tmp/reviewlens-monitoring/grafana.log 2>&1 &

GRAFANA_PID=$!
echo "   ✓ Grafana 시작됨 (PID: $GRAFANA_PID)"
echo "   📝 로그: /tmp/reviewlens-monitoring/grafana.log"

# 7. 서비스 시작 대기
echo ""
echo "⏳ 서비스 시작 대기 중... (5초)"
sleep 5

# 8. 헬스체크
echo ""
echo "🔄 Step 6: 헬스체크"

# Prometheus 헬스체크
echo "   🔍 Prometheus 상태 확인..."
if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo "   ✅ Prometheus: http://localhost:9090 (Healthy)"
else
    echo "   ❌ Prometheus: 응답 없음"
    echo "      로그 확인: tail -20 /tmp/reviewlens-monitoring/prometheus.log"
fi

# Grafana 헬스체크
echo "   🔍 Grafana 상태 확인..."
if curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
    GRAFANA_VERSION=$(curl -s http://localhost:3001/api/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('version', 'unknown'))" 2>/dev/null || echo "unknown")
    echo "   ✅ Grafana: http://localhost:3001 (v$GRAFANA_VERSION)"
else
    echo "   ❌ Grafana: 응답 없음"
    echo "      로그 확인: tail -20 /tmp/reviewlens-monitoring/grafana.log"
fi

# ReviewLens 백엔드 타겟 확인
echo "   🔍 ReviewLens 백엔드 타겟 확인..."
sleep 3  # Prometheus가 첫 스크랩을 할 시간 제공
TARGET_HEALTH=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for target in data.get('data', {}).get('activeTargets', []):
        if 'reviewlens' in target.get('labels', {}).get('job', ''):
            print(target.get('health', 'unknown'))
            break
    else:
        print('not_found')
except:
    print('error')
" || echo "error")

if [ "$TARGET_HEALTH" = "up" ]; then
    echo "   ✅ ReviewLens Backend: http://localhost:8000/metrics (UP)"
elif [ "$TARGET_HEALTH" = "not_found" ]; then
    echo "   ⚠️  ReviewLens Backend: 타겟을 찾을 수 없습니다"
else
    echo "   ⚠️  ReviewLens Backend: 상태 확인 실패 ($TARGET_HEALTH)"
    echo "      백엔드가 실행 중인지 확인: curl http://localhost:8000/metrics"
fi

# 9. 완료 메시지
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     모니터링 시스템 재시작 완료! 🎉                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 접속 정보:"
echo "   • Prometheus: http://localhost:9090"
echo "   • Grafana:    http://localhost:3001 (admin/admin)"
echo "   • Metrics:    http://localhost:8000/metrics"
echo ""
echo "📝 로그 확인:"
echo "   • Prometheus: tail -f /tmp/reviewlens-monitoring/prometheus.log"
echo "   • Grafana:    tail -f /tmp/reviewlens-monitoring/grafana.log"
echo ""
echo "🛑 중지:"
echo "   • ./scripts/monitor_stop.sh"
echo ""
