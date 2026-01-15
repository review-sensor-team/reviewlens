// API 설정
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default {
  baseURL: API_BASE_URL,
  endpoints: {
    startSession: '/api/chat/start',
    sendMessage: '/api/chat/message',
    collectReviews: '/api/chat/collect-reviews',
    resetSession: '/api/chat/reset-session'
  }
}
