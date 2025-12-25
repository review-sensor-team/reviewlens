# ReviewLens Frontend

Vue 3 + Vite 기반 챗봇 UI

## 개발 환경 설정

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

개발 서버: `http://localhost:5173`

## 빌드

```bash
npm run build
npm run preview
```

## 기능

- 🤖 대화형 챗봇 인터페이스
- 📊 실시간 후회 요인 표시
- ✅ 3-5턴 대화 수렴
- 🎯 최종 분석 결과 표시

## 환경변수

`.env` 파일에서 API URL 설정:
```
VITE_API_URL=http://localhost:8000
```

## 백엔드 연동

FastAPI 서버가 실행 중이어야 합니다:
```bash
cd ../backend
uvicorn app.main:app --reload
```
