#!/bin/bash
# ReviewLens 로컬 서버 재시작 스크립트

echo "🔄 ReviewLens 서버를 재시작합니다..."
echo ""

# 기존 프로세스 종료
echo "🛑 기존 서버 종료 중..."
pkill -f "uvicorn backend.app.main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null

# 포트가 완전히 해제될 때까지 대기
sleep 2

# 포트 강제 해제 (필요한 경우)
if lsof -ti:8000 >/dev/null 2>&1; then
    echo "  ⚠️  포트 8000 강제 해제 중..."
    kill -9 $(lsof -ti:8000) 2>/dev/null
fi

if lsof -ti:5173 >/dev/null 2>&1; then
    echo "  ⚠️  포트 5173 강제 해제 중..."
    kill -9 $(lsof -ti:5173) 2>/dev/null
fi

echo "  ✓ 기존 서버 종료 완료"
echo ""

# 로그 디렉토리 생성
mkdir -p logs

# 백엔드 서버 시작
echo "📦 백엔드 서버 시작 중... (포트 8000)"
cd "$(dirname "$0")"
source .venv/bin/activate
nohup uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "  ✓ 백엔드 서버 시작됨 (PID: $BACKEND_PID)"
echo "  📄 로그: logs/backend.log"

# 백엔드 시작 확인
sleep 3
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo "  ✅ 백엔드 서버 정상 실행 중"
else
    echo "  ❌ 백엔드 서버 시작 실패 (로그 확인 필요)"
    tail -20 logs/backend.log
    exit 1
fi

echo ""

# 프론트엔드 서버 시작
echo "🎨 프론트엔드 서버 시작 중... (포트 5173)"
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "  ✓ 프론트엔드 서버 시작됨 (PID: $FRONTEND_PID)"
echo "  📄 로그: logs/frontend.log"

# 프론트엔드 시작 확인
sleep 3
if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo "  ✅ 프론트엔드 서버 정상 실행 중"
else
    echo "  ❌ 프론트엔드 서버 시작 실패 (로그 확인 필요)"
    tail -20 logs/frontend.log
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ReviewLens 서버 재시작 완료!"
echo ""
echo "🌐 접속 URL:"
echo "   백엔드:      http://localhost:8000"
echo "   API 문서:    http://localhost:8000/docs"
echo "   프론트엔드:  http://localhost:5173"
echo ""
echo "� 서버 중지: ./local_stop.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 실시간 로그 모니터링 시작..."
echo "📊 로그 확인:"
echo "   tail -f logs/app.log      # 전체 애플리케이션 로그"
echo "   tail -f logs/api.log       # API 요청/응답 로그"
echo "   tail -f logs/pipeline.log  # 파이프라인 처리 로그"
echo "   tail -f logs/error.log     # 에러 로그만"
echo ""
echo "💡 서버가 백그라운드에서 실행 중입니다"
echo "   터미널을 닫아도 서버는 계속 실행됩니다"
echo ""
