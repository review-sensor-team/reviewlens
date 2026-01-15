import api from '../api'
import config from '../config'

/**
 * 세션 시작 (URL 입력 → 후회 포인트 도출)
 */
export const startSession = async (productUrl) => {
  const response = await api.post(config.endpoints.collectReviews, {
    product_url: productUrl,
    max_reviews: 100,
    sort_by_low_rating: true
  })

  // 백엔드 응답에서 후회 포인트(suggested_factors) 추출
  const data = response.data
  const suggestedFactors = data.suggested_factors || []

  return {
    session_id: data.session_id,
    suggested_factors: suggestedFactors,
    product_name: data.product_name || '이 상품',
    total_count: data.total_count || 0,
    raw: data
  }
}

/**
 * 메시지 전송 (후회 포인트 선택 또는 추가 질문)
 */
export const sendMessage = async (sessionId, message, selectedFactor = null) => {
  const payload = {
    session_id: sessionId,
    message
  }
  
  // 후회 포인트를 선택한 경우 selected_factor 추가
  if (selectedFactor) {
    payload.selected_factor = selectedFactor
  }
  
  const response = await api.post(config.endpoints.sendMessage, payload)

  const data = response.data

  // choices가 "|"로 구분된 문자열인 경우 배열로 변환
  let options = null
  if (data.choices) {
    if (typeof data.choices === 'string') {
      options = data.choices.split('|').map(opt => opt.trim()).filter(opt => opt.length > 0)
    } else if (Array.isArray(data.choices)) {
      options = data.choices
    }
  }

  return {
    session_id: data.session_id,
    bot_message: data.bot_message || data.question_text || data.message,
    is_final: Boolean(data.is_final),
    has_analysis: Boolean(data.has_analysis),
    options: options,
    related_reviews: data.related_reviews || null,
    llm_context: data.llm_context || null,
    raw: data
  }
}

/**
 * 세션 재분석 (대화만 초기화, 리뷰 데이터 유지)
 */
export const resetSession = async (sessionId) => {
  const response = await api.post(config.endpoints.resetSession, {
    session_id: sessionId
  })
  return response.data
}
