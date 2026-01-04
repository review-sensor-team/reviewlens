#!/bin/bash
# ReviewLens 모니터링 스택 시작 스크립트
# Prometheus와 Grafana를 로컬 바이너리로 실행

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MONITORING_DIR="$PROJECT_ROOT/monitoring"
BIN_DIR="$MONITORING_DIR/bin"
DATA_DIR="$MONITORING_DIR/data"

echo "🚀 ReviewLens 모니터링 스택 시작 중..."

# 디렉토리 생성
mkdir -p "$BIN_DIR"
mkdir -p "$DATA_DIR/prometheus"
mkdir -p "$DATA_DIR/grafana"

# OS 감지
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Darwin)
        PROM_OS="darwin"
        GRAFANA_OS="darwin"
        ;;
    Linux)
        PROM_OS="linux"
        GRAFANA_OS="linux"
        ;;
    *)
        echo "❌ 지원하지 않는 OS: $OS"
        exit 1
        ;;
esac

case "$ARCH" in
    x86_64)
        PROM_ARCH="amd64"
        GRAFANA_ARCH="amd64"
        ;;
    arm64|aarch64)
        PROM_ARCH="arm64"
        GRAFANA_ARCH="arm64"
        ;;
    *)
        echo "❌ 지원하지 않는 아키텍처: $ARCH"
        exit 1
        ;;
esac

# 버전
PROMETHEUS_VERSION="2.48.1"
GRAFANA_VERSION="10.2.3"

# Prometheus 다운로드 및 설치
if [ ! -f "$BIN_DIR/prometheus" ]; then
    echo "📥 Prometheus 다운로드 중..."
    PROM_ARCHIVE="prometheus-${PROMETHEUS_VERSION}.${PROM_OS}-${PROM_ARCH}.tar.gz"
    PROM_URL="https://github.com/prometheus/prometheus/releases/download/v${PROMETHEUS_VERSION}/${PROM_ARCHIVE}"
    
    cd "$BIN_DIR"
    curl -LO "$PROM_URL"
    tar -xzf "$PROM_ARCHIVE"
    mv "prometheus-${PROMETHEUS_VERSION}.${PROM_OS}-${PROM_ARCH}/prometheus" .
    mv "prometheus-${PROMETHEUS_VERSION}.${PROM_OS}-${PROM_ARCH}/promtool" .
    rm -rf "prometheus-${PROMETHEUS_VERSION}.${PROM_OS}-${PROM_ARCH}" "$PROM_ARCHIVE"
    echo "✅ Prometheus 설치 완료"
else
    echo "✅ Prometheus 이미 설치됨"
fi

# Grafana 다운로드 및 설치
if [ ! -d "$BIN_DIR/grafana" ]; then
    echo "📥 Grafana 다운로드 중..."
    GRAFANA_ARCHIVE="grafana-${GRAFANA_VERSION}.${GRAFANA_OS}-${GRAFANA_ARCH}.tar.gz"
    GRAFANA_URL="https://dl.grafana.com/oss/release/${GRAFANA_ARCHIVE}"
    
    cd "$BIN_DIR"
    curl -LO "$GRAFANA_URL"
    tar -xzf "$GRAFANA_ARCHIVE"
    mv "grafana-${GRAFANA_VERSION}" grafana
    rm "$GRAFANA_ARCHIVE"
    echo "✅ Grafana 설치 완료"
else
    echo "✅ Grafana 이미 설치됨"
fi

# Grafana 설정 파일 복사
if [ -f "$MONITORING_DIR/grafana.ini" ]; then
    cp "$MONITORING_DIR/grafana.ini" "$BIN_DIR/grafana/conf/custom.ini"
fi

# 이미 실행 중인 프로세스 확인 및 종료
echo "🔍 기존 프로세스 확인 중..."
if pgrep -f "prometheus.*monitoring/prometheus.yml" > /dev/null; then
    echo "⚠️  기존 Prometheus 프로세스 발견, 종료 중..."
    pkill -f "prometheus.*monitoring/prometheus.yml" || true
    sleep 2
fi

if pgrep -f "grafana-server" > /dev/null; then
    echo "⚠️  기존 Grafana 프로세스 발견, 종료 중..."
    pkill -f "grafana-server" || true
    sleep 2
fi

# Prometheus 시작
echo "🔧 Prometheus 시작 중... (포트 9090)"
cd "$PROJECT_ROOT"
nohup "$BIN_DIR/prometheus" \
    --config.file="$MONITORING_DIR/prometheus.yml" \
    --storage.tsdb.path="$DATA_DIR/prometheus" \
    --web.console.libraries="$BIN_DIR/console_libraries" \
    --web.console.templates="$BIN_DIR/consoles" \
    --web.enable-lifecycle \
    > "$DATA_DIR/prometheus/prometheus.log" 2>&1 &

PROM_PID=$!
echo "  PID: $PROM_PID"
sleep 2

# Prometheus 헬스 체크
if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
    echo "✅ Prometheus 실행 중 (http://localhost:9090)"
else
    echo "⚠️  Prometheus 헬스 체크 실패 (재시도 중...)"
    sleep 3
    if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
        echo "✅ Prometheus 실행 중 (http://localhost:9090)"
    else
        echo "❌ Prometheus 시작 실패. 로그를 확인하세요: $DATA_DIR/prometheus/prometheus.log"
    fi
fi

# Grafana 시작
echo "🔧 Grafana 시작 중... (포트 3001)"
nohup "$BIN_DIR/grafana/bin/grafana-server" \
    --homepath="$BIN_DIR/grafana" \
    --config="$BIN_DIR/grafana/conf/custom.ini" \
    web \
    > "$DATA_DIR/grafana/grafana.log" 2>&1 &

GRAFANA_PID=$!
echo "  PID: $GRAFANA_PID"
sleep 3

# Grafana 헬스 체크
if curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
    echo "✅ Grafana 실행 중 (http://localhost:3001)"
else
    echo "⚠️  Grafana 헬스 체크 실패 (시작 중...)"
    sleep 5
    if curl -s http://localhost:3001/api/health > /dev/null 2>&1; then
        echo "✅ Grafana 실행 중 (http://localhost:3001)"
    else
        echo "❌ Grafana 시작 실패. 로그를 확인하세요: $DATA_DIR/grafana/grafana.log"
    fi
fi

# PID 저장
echo $PROM_PID > "$DATA_DIR/prometheus.pid"
echo $GRAFANA_PID > "$DATA_DIR/grafana.pid"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 모니터링 스택 시작 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 접속 정보:"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana:    http://localhost:3001"
echo "               (ID: admin / PW: admin)"
echo ""
echo "📁 로그 파일:"
echo "  - Prometheus: $DATA_DIR/prometheus/prometheus.log"
echo "  - Grafana:    $DATA_DIR/grafana/grafana.log"
echo ""
echo "🛑 종료: ./scripts/stop_monitoring.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
