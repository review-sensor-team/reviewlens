import axios from 'axios'
import config from './config'

const api = axios.create({
  baseURL: config.baseURL,
  timeout: 120000, // 리뷰 수집은 시간이 걸릴 수 있으므로 2분으로 증가
  headers: { 'Content-Type': 'application/json' }
})

function normalizeChatResponse(data) {
  const d = data || {}

  const top_factors = Array.isArray(d.top_factors)
    ? d.top_factors.map(f => {
        // ["noise_sleep", 1.2] 같은 형태도 수용
        if (Array.isArray(f)) {
          return { factor_key: f[0], score: Number(f[1] ?? 0), display_name: f[0] }
        }
        return {
          factor_key: f.factor_key,
          score: Number(f.score ?? 0),
          display_name: f.display_name || f.factor_key
        }
      })
    : []

  // 백엔드가 bot_message 대신 question_text/message로 줄 수도 있으니 흡수
  const bot_message =
    d.bot_message ||
    d.question_text ||
    d.message ||
    (d.is_final ? '분석이 완료되었습니다.' : '다음 질문을 진행할게요.')

  return {
    session_id: d.session_id ?? null,
    is_final: Boolean(d.is_final),
    bot_message,
    top_factors,
    llm_context: d.llm_context ?? null,
    related_reviews: d.related_reviews ?? null,  // ✅ 추가
    question_text: d.question_text ?? bot_message,  // ✅ 추가
    question_id: d.question_id ?? null,  // ✅ 추가
    answer_type: d.answer_type ?? null,  // ✅ 추가
    choices: d.choices ?? null,  // ✅ 추가
    _raw: d
  }
}

// 세션 시작 (v2 API)
export const startChatSession = async (category, productName = '상품') => {
  const response = await api.post(config.endpoints.createSession, { 
    category: category || '전자기기',
    product_name: productName 
  })
  
  // v2 응답 구조
  const data = response.data
  return { 
    session_id: data.session_id, 
    category: data.category,
    product_name: data.product_name,
    message: '세션이 생성되었습니다.',
    _raw: data 
  }
}

// 메시지 전송 (v2 API)
export const sendMessage = async (sessionId, message, selectedFactor = null) => {
  const payload = {
    session_id: sessionId,
    user_message: message
  }
  
  // 후회 포인트 선택 시
  if (selectedFactor) {
    payload.selected_factor = selectedFactor
  }
  
  const response = await api.post(config.endpoints.sendMessage, payload)
  const data = response.data
  
  return {
    session_id: data.session_id,
    bot_message: data.response || data.message || '응답을 생성했습니다.',
    is_final: Boolean(data.is_final),
    turn_count: data.turn_count || 0,
    _raw: data
  }
}

// 리뷰 수집 (v2 API)
export const collectReviews = async (productUrl, vendor = 'smartstore', productId = null, maxReviews = 100) => {
  const payload = {
    vendor: vendor,
    product_id: productId || 'unknown',
    max_reviews: maxReviews,
    use_collector: Boolean(productUrl),  // URL이 있으면 크롤러 사용
    product_url: productUrl || null
  }
  
  const response = await api.post(config.endpoints.collectReviews, payload)
  const data = response.data
  
  return {
    success: data.success,
    review_count: data.review_count,
    source: data.source,  // 'storage', 'collector', 'sample'
    vendor: data.vendor,
    product_id: data.product_id,
    reviews: data.data || [],
    _raw: data
  }
}

// 리뷰 분석 (v2 API - 신규)
export const analyzeReviews = async (reviews, category = '전자기기', productId = null, saveResults = false) => {
  const payload = {
    reviews: reviews,
    category: category,
    product_id: productId,
    save_results: saveResults
  }
  
  const response = await api.post(config.endpoints.analyzeReviews, payload)
  const data = response.data
  
  return {
    success: data.success,
    factor_count: data.factor_count,
    top_factors: data.top_factors || [],
    category: data.category,
    _raw: data
  }
}

export default api