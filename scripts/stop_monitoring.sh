#!/bin/bash
# ReviewLens 모니터링 스택 중지 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_ROOT/monitoring/data"

echo "🛑 ReviewLens 모니터링 스택 중지 중..."

# PID 파일에서 중지
if [ -f "$DATA_DIR/prometheus.pid" ]; then
    PROM_PID=$(cat "$DATA_DIR/prometheus.pid")
    if kill -0 $PROM_PID 2>/dev/null; then
        echo "  Prometheus (PID: $PROM_PID) 중지 중..."
        kill $PROM_PID
        sleep 1
        if kill -0 $PROM_PID 2>/dev/null; then
            kill -9 $PROM_PID 2>/dev/null || true
        fi
        echo "  ✅ Prometheus 중지됨"
    else
        echo "  ⚠️  Prometheus 프로세스가 이미 중지됨"
    fi
    rm "$DATA_DIR/prometheus.pid"
else
    # PID 파일 없으면 프로세스 이름으로 찾아서 종료
    if pgrep -f "prometheus.*monitoring/prometheus.yml" > /dev/null; then
        echo "  Prometheus 프로세스 발견, 중지 중..."
        pkill -f "prometheus.*monitoring/prometheus.yml"
        sleep 1
        echo "  ✅ Prometheus 중지됨"
    else
        echo "  ℹ️  실행 중인 Prometheus 없음"
    fi
fi

if [ -f "$DATA_DIR/grafana.pid" ]; then
    GRAFANA_PID=$(cat "$DATA_DIR/grafana.pid")
    if kill -0 $GRAFANA_PID 2>/dev/null; then
        echo "  Grafana (PID: $GRAFANA_PID) 중지 중..."
        kill $GRAFANA_PID
        sleep 1
        if kill -0 $GRAFANA_PID 2>/dev/null; then
            kill -9 $GRAFANA_PID 2>/dev/null || true
        fi
        echo "  ✅ Grafana 중지됨"
    else
        echo "  ⚠️  Grafana 프로세스가 이미 중지됨"
    fi
    rm "$DATA_DIR/grafana.pid"
else
    # PID 파일 없으면 프로세스 이름으로 찾아서 종료
    if pgrep -f "grafana-server" > /dev/null; then
        echo "  Grafana 프로세스 발견, 중지 중..."
        pkill -f "grafana-server"
        sleep 1
        echo "  ✅ Grafana 중지됨"
    else
        echo "  ℹ️  실행 중인 Grafana 없음"
    fi
fi

echo ""
echo "✅ 모니터링 스택 중지 완료"
