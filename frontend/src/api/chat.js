import api from '../api'
import config from '../config'

/**
 * 세션 시작 (v2 API: 세션 생성 + 리뷰 수집)
 */
export const startSession = async (productUrl, category = '전자기기', productName = '상품') => {
  // 1. 세션 생성
  const sessionResponse = await api.post(config.endpoints.createSession, {
    category: category,
    product_name: productName
  })
  
  const sessionId = sessionResponse.data.session_id
  
  // 2. 리뷰 수집
  const reviewResponse = await api.post(config.endpoints.collectReviews, {
    vendor: 'smartstore',
    product_id: sessionId,
    max_reviews: 100,
    use_collector: Boolean(productUrl),
    product_url: productUrl
  })
  
  const reviewData = reviewResponse.data
  
  // 3. 리뷰 분석 (후회 포인트 도출)
  let suggestedFactors = []
  if (reviewData.success && reviewData.data && reviewData.data.length > 0) {
    const analyzeResponse = await api.post(config.endpoints.analyzeReviews, {
      reviews: reviewData.data.slice(0, 50),  // 최대 50건만 분석
      category: category,
      product_id: sessionId,
      save_results: true
    })
    
    suggestedFactors = analyzeResponse.data.top_factors || []
  }
  
  return {
    session_id: sessionId,
    suggested_factors: suggestedFactors,
    product_name: productName,
    total_count: reviewData.review_count || 0,
    source: reviewData.source,
    raw: {
      session: sessionResponse.data,
      reviews: reviewData,
      analysis: suggestedFactors
    }
  }
}

/**
 * 메시지 전송 (v2 API: 후회 포인트 선택 또는 추가 질문)
 */
export const sendMessage = async (sessionId, message, selectedFactor = null) => {
  const payload = {
    session_id: sessionId,
    user_message: message
  }
  
  // 후회 포인트를 선택한 경우 selected_factor 추가
  if (selectedFactor) {
    payload.selected_factor = selectedFactor
  }
  
  const response = await api.post(config.endpoints.sendMessage, payload)
  const data = response.data
  
  // v2 응답 구조 매핑
  return {
    session_id: data.session_id,
    bot_message: data.response || data.message || '응답을 생성했습니다.',
    is_final: Boolean(data.is_final),
    turn_count: data.turn_count || 0,
    has_analysis: data.turn_count >= 5,  // 5턴 이상이면 분석 완료로 간주
    options: null,  // v2에서는 options 미지원 (향후 추가)
    related_reviews: data.related_reviews || null,
    llm_context: data.context || null,
    raw: data
  }
}

/**
 * 세션 재분석 (v2 API: 세션 삭제 후 재생성)
 */
export const resetSession = async (sessionId, category = '전자기기', productName = '상품') => {
  // 기존 세션 삭제
  try {
    await api.delete(config.endpoints.deleteSession(sessionId))
  } catch (error) {
    console.warn('세션 삭제 실패 (무시):', error)
  }
  
  // 새 세션 생성
  const response = await api.post(config.endpoints.createSession, {
    category: category,
    product_name: productName
  })
  
  return {
    session_id: response.data.session_id,
    message: '세션이 재설정되었습니다.',
    raw: response.data
  }
}

/**
 * 분석 가능한 상품 목록 조회 (v2 API)
 */
export const getProducts = async () => {
  try {
    const response = await api.get(config.endpoints.getProducts)
    const data = response.data
    
    return data.products || []
  } catch (error) {
    console.error('상품 목록 조회 실패:', error)
    // Fallback: 빈 배열 반환
    return []
  }
}

/**
 * 앱 설정 조회 (v2 API)
 */
export const getAppConfig = async () => {
  try {
    const response = await api.get(config.endpoints.getConfig)
    const data = response.data
    return {
      use_product_selection: data.use_product_selection || true,
      mode: data.mode || 'product_selection'
    }
  } catch (error) {
    console.warn('설정 조회 실패:', error)
    // 기본값: 상품 선택 모드 (USE_PRODUCT_SELECTION=True)
    return { 
      use_product_selection: true,
      mode: 'product_selection' 
    }
  }
}

/**
 * 상품명으로 리뷰 분석 시작 (JSON 파일 로드 방식)
 */
export const analyzeProduct = async (productName) => {
  const response = await api.post(config.endpoints.analyzeProduct, null, {
    params: { product_name: productName }
  })

  const data = response.data
  const suggestedFactors = data.suggested_factors || []

  return {
    session_id: data.session_id,
    suggested_factors: suggestedFactors,
    product_name: data.product_name || productName,
    total_count: data.total_count || 0,
    raw: data
  }
}

