#!/bin/bash
# ReviewLens 로컬 서버 중지 스크립트

echo "🛑 ReviewLens 서버를 중지합니다..."

# 백엔드 (uvicorn) 프로세스 종료
echo "📦 백엔드 서버 종료 중..."
pkill -f "uvicorn backend.app.main:app" && echo "  ✓ 백엔드 서버 종료됨" || echo "  ℹ️  실행 중인 백엔드 서버 없음"

# 프론트엔드 (vite) 프로세스 종료
echo "🎨 프론트엔드 서버 종료 중..."
pkill -f "vite" && echo "  ✓ 프론트엔드 서버 종료됨" || echo "  ℹ️  실행 중인 프론트엔드 서버 없음"

# 포트 확인
echo ""
echo "🔍 포트 사용 현황 확인..."
lsof -ti:8000 >/dev/null 2>&1 && echo "  ⚠️  포트 8000이 여전히 사용 중입니다" || echo "  ✓ 포트 8000 해제됨"
lsof -ti:5173 >/dev/null 2>&1 && echo "  ⚠️  포트 5173이 여전히 사용 중입니다" || echo "  ✓ 포트 5173 해제됨"

echo ""
echo "✅ 서버 중지 완료"
