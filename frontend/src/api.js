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

// 세션 시작
export const startChatSession = async (category) => {
  const response = await api.post(config.endpoints.startSession, { category })
  const norm = normalizeChatResponse(response.data)
  return { session_id: norm.session_id, message: norm.bot_message, _raw: norm._raw }
}

// 메시지 전송
export const sendMessage = async (sessionId, message) => {
  const response = await api.post(config.endpoints.sendMessage, {
    session_id: sessionId,
    message
  })
  return normalizeChatResponse(response.data)
}

// 리뷰 수집
export const collectReviews = async (productUrl, maxReviews = 100, sortByLowRating = true, category = null) => {
  const payload = {
    product_url: productUrl,
    max_reviews: maxReviews,
    sort_by_low_rating: sortByLowRating
  }
  
  // category가 지정되면 추가
  if (category) {
    payload.category = category
  }
  
  const response = await api.post(config.endpoints.collectReviews, payload)
  return response.data
}

export default api