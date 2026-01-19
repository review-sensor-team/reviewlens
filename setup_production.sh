#!/bin/bash
# ReviewLens 프로덕션 배포 퀵 스타트 스크립트

set -e

echo "🚀 ReviewLens 프로덕션 배포 설정 시작..."

# 1. 환경 확인
echo ""
echo "📋 1. 환경 확인 중..."

if ! command -v git &> /dev/null; then
    echo "❌ Git이 설치되지 않았습니다."
    exit 1
fi
echo "✅ Git 설치됨"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되지 않았습니다."
    exit 1
fi
echo "✅ Python3 설치됨"

if ! command -v node &> /dev/null; then
    echo "❌ Node.js가 설치되지 않았습니다."
    exit 1
fi
echo "✅ Node.js 설치됨"

# 2. .env 파일 생성
echo ""
echo "📝 2. 환경 설정 파일 생성 중..."

if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ .env 파일 생성됨"
    echo "⚠️  .env 파일을 수정하여 프로덕션 설정을 입력하세요"
else
    echo "✅ .env 파일이 이미 존재합니다"
fi

# 3. Python 가상환경 설정
echo ""
echo "🐍 3. Python 가상환경 설정 중..."

cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 가상환경 생성됨"
fi

source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ Python 의존성 설치 완료"
cd ..

# 4. Frontend 빌드
echo ""
echo "⚛️  4. Frontend 빌드 중..."

cd frontend
npm install --quiet
npm run build
echo "✅ Frontend 빌드 완료"
cd ..

# 5. 디렉토리 권한 설정
echo ""
echo "🔒 5. 권한 설정 중..."

chmod +x local_restart.sh local_stop.sh
chmod +x db_start.sh db_stop.sh 2>/dev/null || true
chmod +x scripts/*.sh 2>/dev/null || true
echo "✅ 실행 권한 설정 완료"

# 6. 로그 디렉토리 생성
echo ""
echo "📁 6. 로그 디렉토리 생성 중..."

mkdir -p logs
mkdir -p backend/data/{review,factor,question}
echo "✅ 필요한 디렉토리 생성 완료"

# 완료
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 프로덕션 배포 준비 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "다음 단계:"
echo "1. .env 파일 수정하여 프로덕션 설정 입력"
echo "2. ./local_restart.sh 실행하여 서비스 시작"
echo "3. http://localhost:8000/metrics 접속하여 확인"
echo ""
echo "GitHub Actions 자동 배포 설정:"
echo "- docs/DEPLOYMENT.md 문서 참고"
echo "- GitHub Secrets 설정 필요"
echo ""
