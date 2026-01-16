#!/bin/bash

# ReviewLens 모니터링 시스템 중지 스크립트

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ReviewLens 모니터링 시스템 중지                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Prometheus 중지
echo "🔴 Prometheus 중지 중..."
if pgrep -f "prometheus.*config.file" > /dev/null; then
    pkill -f "prometheus.*config.file"
    echo "   ✓ Prometheus 프로세스 종료됨"
else
    echo "   ℹ Prometheus가 실행 중이 아닙니다"
fi

# Grafana 중지
echo "🔴 Grafana 중지 중..."
if pgrep -f "grafana.*server" > /dev/null; then
    pkill -f "grafana.*server"
    echo "   ✓ Grafana 프로세스 종료됨"
else
    echo "   ℹ Grafana가 실행 중이 아닙니다"
fi

# 프로세스 종료 대기
sleep 2

# 종료 확인
echo ""
echo "📊 프로세스 상태 확인:"
PROM_RUNNING=$(pgrep -f "prometheus.*config.file" || true)
GRAFANA_RUNNING=$(pgrep -f "grafana.*server" || true)

if [ -z "$PROM_RUNNING" ] && [ -z "$GRAFANA_RUNNING" ]; then
    echo "   ✅ 모든 모니터링 프로세스가 종료되었습니다"
else
    if [ -n "$PROM_RUNNING" ]; then
        echo "   ⚠️  Prometheus가 여전히 실행 중입니다 (PID: $PROM_RUNNING)"
        echo "      강제 종료: kill -9 $PROM_RUNNING"
    fi
    if [ -n "$GRAFANA_RUNNING" ]; then
        echo "   ⚠️  Grafana가 여전히 실행 중입니다 (PID: $GRAFANA_RUNNING)"
        echo "      강제 종료: kill -9 $GRAFANA_RUNNING"
    fi
fi

echo ""
echo "✅ 모니터링 시스템 중지 완료"
