// API 설정
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Clean Architecture v2.0 API
export default {
  baseURL: API_BASE_URL,
  apiVersion: 'v2',  // API 버전
  endpoints: {
    // v2 Chat API
    createSession: '/api/v2/chat/sessions',
    sendMessage: '/api/v2/chat/messages',
    getSession: (sessionId) => `/api/v2/chat/sessions/${sessionId}`,
    deleteSession: (sessionId) => `/api/v2/chat/sessions/${sessionId}`,
    
    // v2 Review API
    collectReviews: '/api/v2/reviews/collect',
    analyzeReviews: '/api/v2/reviews/analyze',
    analyzeProduct: '/api/v2/reviews/analyze-product',  // 상품명으로 리뷰 분석
    getProducts: '/api/v2/reviews/products',  // 상품 목록 조회
    getConfig: '/api/v2/reviews/config',  // 앱 설정 조회
    
    // Legacy v1 API (하위 호환성)
    legacy: {
      startSession: '/api/chat/start',
      sendMessage: '/api/chat/message',
      collectReviews: '/api/chat/collect-reviews'
    }
  }
}

