import { ref, nextTick, onMounted, computed } from 'vue'
import { startSession, sendMessage, resetSession, getProducts, analyzeProduct, getAppConfig } from '../api/chat.js'
import { marked } from 'marked'
import config from '../config.js'

export function useReviewLens() {
  // Marked 옵션 설정
  marked.setOptions({
    breaks: true, // 줄바꿈을 <br>로 변환
    gfm: true // GitHub Flavored Markdown 사용
  })

  // State
  const messages = ref([])
  const input = ref('')
  const loading = ref(false)
  const loadingText = ref('')
  const loadingType = ref('search') // 'search', 'analyze', 'error', 'alert'
  const scrollRef = ref(null)
  const loadingStartTime = ref(null)
  const loadingElapsedSeconds = ref(0)
  let loadingInterval = null

  const sessionId = ref(null)
  const availableProducts = ref([])
  const analysisMode = ref(null) // null, 'product', 'url'
  const useProductSelection = ref(false) // settings에서 가져올 값
  const waitingForNewAnalysisResponse = ref(false) // "다른 상품 분석?" 질문 대기 중
  const strategyNames = ref({}) // 전략 이름 한글 매핑
  const factorsMap = ref({}) // factor_key -> display_name 매핑

  // Computed
  const welcomeMessage = computed(() => {
    if (useProductSelection.value) {
      return '아래의 상품 중 분석할 상품을 선택해 주세요.'
    } else {
      return '제가 분석할 상품을 선택하거나 URL을 입력해주세요.'
    }
  })

  // Lifecycle
  onMounted(async () => {
    try {
      // 앱 설정 로드
      const config = await getAppConfig()
      useProductSelection.value = config.use_product_selection
      strategyNames.value = config.strategy_names || {}
      
      // 상품 선택 모드면 자동으로 상품 목록 로드
      if (useProductSelection.value) {
        analysisMode.value = 'product'
        loading.value = true
        loadingType.value = 'search'
        loadingText.value = '상품 목록을 불러오는 중이에요...'
        try {
          availableProducts.value = await getProducts()
          console.log('상품 목록 로드:', availableProducts.value)
        } catch (error) {
          console.error('상품 목록 로드 실패:', error)
        } finally {
          loading.value = false
        }
      }
    } catch (error) {
      console.error('설정 로드 실패:', error)
    }
  })

  // Helper Functions
  const scrollBottom = async () => {
    await nextTick()
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  }

  const startLoadingTimer = () => {
    loadingStartTime.value = Date.now()
    loadingElapsedSeconds.value = 0
    
    if (loadingInterval) {
      clearInterval(loadingInterval)
    }
    
    loadingInterval = setInterval(() => {
      if (loadingStartTime.value) {
        loadingElapsedSeconds.value = Math.floor((Date.now() - loadingStartTime.value) / 1000)
      }
    }, 1000)
  }

  const stopLoadingTimer = () => {
    if (loadingInterval) {
      clearInterval(loadingInterval)
      loadingInterval = null
    }
    loadingStartTime.value = null
    loadingElapsedSeconds.value = 0
  }

  const formatTimestamp = () => {
    const now = new Date()
    const month = now.getMonth() + 1
    const day = now.getDate()
    const period = now.getHours() >= 12 ? '오후' : '오전'
    let hours = now.getHours() % 12
    if (hours === 0) hours = 12
    const minutes = String(now.getMinutes()).padStart(2, '0')
    return `${month}/${day} ${period} ${hours}:${minutes}`
  }

  const convertMarkdownToHtml = (markdown) => {
    if (!markdown) return ''
    return marked(markdown)
  }

  const cleanJsonString = (jsonString) => {
    if (!jsonString) return ''
    
    let cleaned = jsonString.trim()
    
    // 시작 부분의 ```json 또는 ``` 제거
    cleaned = cleaned.replace(/^```json\s*/i, '')
    cleaned = cleaned.replace(/^```\s*/, '')
    
    // 끝 부분의 ``` 제거
    cleaned = cleaned.replace(/\s*```$/, '')
    
    return cleaned.trim()
  }

  const getStrategyNameInKorean = (strategyName) => {
    if (strategyNames.value && strategyNames.value[strategyName]) {
      return strategyNames.value[strategyName]
    }
    
    const fallbackMap = {
      'default': '기본형',
      'concise': '간결형',
      'detailed': '상세형',
      'friendly': '친근형',
      'custom': '맞춤형'
    }
    return fallbackMap[strategyName] || strategyName
  }

  const getRiskLabel = (riskLevel) => {
    const labels = {
      'high': '높음',
      'mid': '중간',
      'low': '낮음'
    }
    return labels[riskLevel] || riskLevel
  }

  const replaceFactorKeysWithDisplayNames = (analysisJson) => {
    if (analysisJson.key_findings && Array.isArray(analysisJson.key_findings)) {
      analysisJson.key_findings.forEach(finding => {
        if (finding.factor_key && factorsMap.value[finding.factor_key]) {
          finding.factor = factorsMap.value[finding.factor_key]
        } else if (finding.factor && factorsMap.value[finding.factor]) {
          finding.factor = factorsMap.value[finding.factor]
        }
      })
    }
    return analysisJson
  }

  const getLoadingIcon = () => {
    const icons = {
      search: '/images/ic_search.png',
      analyze: '/images/ic_file-text.png',
      error: '/images/ic_x-circle.png',
      alert: '/images/ic_alert-circle.png',
      brief: '/images/ic_file-text.png'
    }
    return icons[loadingType.value] || icons.search
  }

  const getMessageIcon = (type) => {
    const icons = {
      search: '/images/ic_search.png',
      analyze: '/images/ic_file-text.png',
      error: '/images/ic_x-circle.png',
      alert: '/images/ic_alert-circle.png'
    }
    return icons[type] || null
  }

  const pushBot = (text, options = null, regretPoints = null, reviews = null, messageType = null, reviewSummary = null, questionId = null, factorKey = null, showRating = false, responseFile = null, strategy = null, analysisData = null) => {
    messages.value.push({ 
      role: 'bot', 
      text, 
      options, 
      regretPoints, 
      reviews,
      messageType,
      analysisData,
      reviewSummary,
      questionId,
      factorKey,
      showRating,
      responseFile,
      strategy,
      hoverRating: 0,
      timestamp: formatTimestamp()
    })
    scrollBottom()
  }

  const pushUser = (text, rating = null) => {
    const userMsg = { 
      role: 'user', 
      text,
      timestamp: formatTimestamp()
    }
    
    if (rating) {
      const stars = Array(rating).fill('<img src="/images/ic_star_filled.svg" alt="별" style="width: 16px; height: 16px; display: inline-block; vertical-align: middle; margin: 0 1px;">').join('')
      if (text) {
        userMsg.text = `${text}: ${stars}`
      } else {
        userMsg.text = stars
      }
    }
    
    messages.value.push(userMsg)
    scrollBottom()
  }

  // Action Handlers
  const showProductSelection = async () => {
    analysisMode.value = 'product'
    if (availableProducts.value.length === 0) {
      loading.value = true
      loadingType.value = 'search'
      loadingText.value = '상품 목록을 불러오는 중이에요...'
      try {
        availableProducts.value = await getProducts()
        console.log('상품 목록 로드:', availableProducts.value)
      } catch (error) {
        console.error('상품 목록 로드 실패:', error)
        pushBot('상품 목록을 불러오는데 실패했어요. 다시 시도해주세요.', null, null, null, 'error')
      } finally {
        loading.value = false
      }
    }
  }

  const showUrlInput = () => {
    analysisMode.value = 'url'
  }

  const submitRating = async (rating, responseFile, strategy = null) => {
    try {
      const targetMessage = messages.value.find(m => 
        m.role === 'bot' && m.showRating && m.responseFile === responseFile
      )
      if (targetMessage) {
        targetMessage.showRating = false
      }
      
      const strategyToSend = strategy || targetMessage?.strategy
      
      let ratingText = ''
      if (strategyToSend) {
        const strategyNameKo = getStrategyNameInKorean(strategyToSend)
        ratingText = `${strategyNameKo} 분석`
      }
      
      pushUser(ratingText, rating)
      
      console.log('별점 전송:', { responseFile, rating, strategy: strategyToSend })
      
      const payload = {
        response_file: responseFile,
        rating: rating
      }
      
      if (strategyToSend) {
        payload.strategy = strategyToSend
      }
      
      const response = await fetch(`${config.baseURL}/api/v2/reviews/rate-response`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })
      
      if (response.ok) {
        console.log('별점 전송 성공:', rating)
        
        const remainingRatings = messages.value.filter(m => m.showRating).length
        
        if (remainingRatings === 0) {
          pushBot('소중한 의견 감사합니다!<br/>다른 상품도 분석해 드릴까요?')
          waitingForNewAnalysisResponse.value = true
        } else {
          pushBot('감사합니다!')
        }
      } else {
        const errorData = await response.json()
        console.error('별점 전송 실패:', response.status, errorData)
        pushBot(`평가를 저장하는데 실패했어요.<br/>오류: ${errorData.detail || '알 수 없는 오류'}`)
      }
    } catch (error) {
      console.error('별점 전송 오류:', error)
      pushBot('평가를 저장하는데 실패했어요.<br/>네트워크 오류가 발생했습니다.')
    }
  }

  const selectProduct = async (productName) => {
    pushUser(productName)
    
    loading.value = true
    startLoadingTimer()
    loadingType.value = 'search'
    loadingText.value = '상품 리뷰를 불러오는 중이에요...'
    
    try {
      const res = await analyzeProduct(productName)
      sessionId.value = res.session_id
      
      console.log('세션 생성 완료:', res.session_id)
      console.log('suggested_factors:', res.suggested_factors)
      
      loadingType.value = 'analyze'
      loadingText.value = '후회 포인트를 분석 중이에요...'
      await new Promise(r => setTimeout(r, 800))
      
      const reviewCount = res.total_count || 0
      pushBot(
        `<span style="color: #017FFF; font-weight: 400;">${productName}</span>의<br />별점 낮은 순으로 ${reviewCount}건에서 후회 포인트를 분석해 보았어요.<br />
아래 키워드를 선택하면 해당 리뷰 키워드와 관련된 리뷰를 보여드릴께요.<br />
혹은 궁금하신 점을 질문해 주시면 관련해서 자세히 설명 드릴께요.`,
        null,
        res.suggested_factors,
        null,
        'analyze'
      )
    } catch (e) {
      console.error('상품 분석 오류:', e)
      
      loadingType.value = 'error'
      loadingText.value = '리뷰 분석에 실패했어요.'
      await new Promise(r => setTimeout(r, 1000))
      
      pushBot(
        '상품 분석 중 오류가 발생했어요.',
        null,
        null,
        null,
        'error'
      )
      pushBot(
        '해당 상품의 리뷰 파일을 찾을 수 없거나<br />분석 중 문제가 발생했어요. 다른 상품을 선택해 주세요.',
        null,
        null,
        null,
        'alert'
      )
      sessionId.value = null
    } finally {
      loading.value = false
      stopLoadingTimer()
    }
  }

  const send = async () => {
    if (!input.value.trim()) return

    const text = input.value
    input.value = ''
    
    if (waitingForNewAnalysisResponse.value) {
      pushUser(text)
      waitingForNewAnalysisResponse.value = false
      
      const positivePatterns = /^(네|yes|응|예|ㅇㅇ|ㅇ|ok|okay|좋아|그래|맞아|분석|새로|다른|할게|할래|해줘|부탁|원해)/i
      const negativePatterns = /^(아니|no|노|ㄴㄴ|ㄴ|싫어|안|됐어|됐|괜찮|필요없|그만|재분석|다시|처음)/i
      
      if (positivePatterns.test(text.trim())) {
        pushBot('알겠습니다! 새로운 상품을 분석해드릴게요. 상품을 선택해주세요.')
        startNewAnalysis()
        return
      } else if (negativePatterns.test(text.trim())) {
        pushBot('알겠습니다! 같은 상품으로 처음부터 다시 시작할게요.')
        await clearConversation()
        return
      } else {
        waitingForNewAnalysisResponse.value = true
        pushBot('"네" 또는 "아니오"로 답변해주세요. 다른 상품을 분석하시겠어요?')
        return
      }
    }
    
    const isUrl = /^https?:\/\/.+/.test(text.trim()) || 
                  /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/.test(text.trim())
    
    if (analysisMode.value === 'url' && isUrl && !sessionId.value) {
      pushUser(text)
      await handleUrlAnalysis(text)
      return
    }
    
    pushUser(text)

    if (!sessionId.value) {
      pushBot('먼저 위에서 분석할 상품을 선택해 주세요.', null, null, null, 'alert')
      return
    }

    loading.value = true
    startLoadingTimer()
    loadingType.value = 'search'
    loadingText.value = '답변을 처리 중이에요...'
    
    try {
      const lastMessage = messages.value[messages.value.length - 2]
      const questionId = lastMessage?.questionId
      const factorKey = lastMessage?.factorKey
      
      const response = await fetch(
        `${config.baseURL}/api/v2/reviews/answer-question/${sessionId.value}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            answer: text,
            question_id: questionId,
            factor_key: factorKey
          })
        }
      )
      
      const data = await response.json()
      
      if (!response.ok || data.detail) {
        console.error('API 에러:', data)
        pushBot('답변을 처리하는 중 오류가 발생했어요.', null, null, null, 'error')
        loading.value = false
        stopLoadingTimer()
        return
      }
      
      if (data.is_converged && data.analysis) {
        if (data.analysis.top_factors && Array.isArray(data.analysis.top_factors)) {
          data.analysis.top_factors.forEach(factor => {
            if (factor.factor_key && factor.display_name) {
              factorsMap.value[factor.factor_key] = factor.display_name
            }
          })
          console.log('[factorsMap 구성 완료]', factorsMap.value)
        }
        
        loadingType.value = 'analyze'
        loadingText.value = '후회 포인트를 분석 중이에요...'
        await new Promise(r => setTimeout(r, 800))
        
        if (data.analysis.llm_summaries && data.analysis.llm_summaries.length > 1) {
          console.log('[다중 전략] 전략 개수:', data.analysis.llm_summaries.length)
          
          for (const strategyResult of data.analysis.llm_summaries) {
            const llmSummary = strategyResult.summary
            const strategyName = strategyResult.strategy
            const strategyNameKo = getStrategyNameInKorean(strategyName)
            const responseFile = strategyResult.response_file
            
            try {
              const cleanedJson = cleanJsonString(llmSummary)
              const analysisJson = JSON.parse(cleanedJson)
              
              replaceFactorKeysWithDisplayNames(analysisJson)
              
              pushBot(
                null,
                null, null, null, 'analyze',
                null, null, null, false, null, null,
                {
                  productName: data.analysis.product_name || '제품',
                  strategyName: strategyNameKo,
                  summary: analysisJson.summary,
                  key_findings: analysisJson.key_findings,
                  balanced_view: analysisJson.balanced_view,
                  decision_rule: analysisJson.decision_rule,
                  final_recommendation: analysisJson.final_recommendation,
                  one_line_tip: analysisJson.one_line_tip
                }
              )
              
              console.log(`[별점 요청] strategy=${strategyName}, responseFile=${responseFile}`)
              
              pushBot(
                `"${strategyNameKo}" 분석에 만족하셨나요? 별점을 남겨주세요!`, 
                null, null, null, null, null, null, null, 
                true,
                responseFile,
                strategyName
              )
            } catch (e) {
              console.error(`[${strategyName}] 분석 결과 파싱 실패:`, e)
              const htmlContent = convertMarkdownToHtml(llmSummary)
              pushBot(htmlContent, null, null, null, 'analyze')
            }
          }
          
          console.log('[다중 전략] 모든 전략 처리 완료')
          
          waitingForNewAnalysisResponse.value = true
          pushBot('다른 상품에 대한 리뷰를 분석해 드릴까요?')
          loading.value = false
          stopLoadingTimer()
          return
        }
        
        const llmSummary = data.analysis.llm_summary
        if (llmSummary) {
          try {
            const cleanedJson = cleanJsonString(llmSummary)
            const analysisJson = JSON.parse(cleanedJson)
            
            replaceFactorKeysWithDisplayNames(analysisJson)
            
            pushBot(
              null,
              null, null, null, 'analyze',
              null, null, null, false, null, null,
              {
                productName: data.analysis.product_name || '제품',
                strategyName: null,
                summary: analysisJson.summary,
                key_findings: analysisJson.key_findings,
                balanced_view: analysisJson.balanced_view,
                decision_rule: analysisJson.decision_rule,
                final_recommendation: analysisJson.final_recommendation,
                one_line_tip: analysisJson.one_line_tip
              }
            )
            
            const responseFile = data.analysis.response_file || `llm_response_${Date.now()}.json`
            pushBot(
              '분석 결과에 만족하셨나요? 별점을 남겨주세요!', 
              null, null, null, null, null, null, null, 
              true,
              responseFile
            )
          } catch (e) {
            console.error('LLM 분석 결과 파싱 실패:', e)
            const htmlContent = convertMarkdownToHtml(llmSummary)
            pushBot(htmlContent, null, null, null, 'analyze')
            
            const responseFile = data.analysis.response_file || `llm_response_${Date.now()}.json`
            pushBot(
              '분석 결과에 만족하셨나요? 별점을 남겨주세요!', 
              null, null, null, null, null, null, null, 
              true,
              responseFile
            )
          }
        } else {
          pushBot('분석이 완료되었습니다.', null, null, null, 'analyze')
        }
      } else if (data.next_question) {
        pushBot(
          data.next_question.question_text,
          data.next_question.choices || null,
          null,
          null,
          null,
          null,
          data.next_question.question_id,
          data.next_question.factor_key
        )
      } else {
        pushBot('질문이 종료되었습니다.', null, null, null, 'alert')
      }
    } catch (e) {
      console.error('답변 처리 오류:', e)
      pushBot('답변을 처리하는 중 오류가 발생했어요.', null, null, null, 'error')
    } finally {
      loading.value = false
      stopLoadingTimer()
    }
  }

  const selectRegretPoint = async (factorKey) => {
    const lastMessage = messages.value[messages.value.length - 1]
    const factor = lastMessage?.regretPoints?.find(f => 
      (typeof f === 'object' && f.factor_key === factorKey) || f === factorKey
    )
    const displayName = typeof factor === 'object' ? factor.display_name : factorKey
    
    pushUser(displayName)
    
    loading.value = true
    startLoadingTimer()
    loadingType.value = 'search'
    loadingText.value = '관련 리뷰를 찾고 있어요...'
    
    try {
      const response = await fetch(`${config.baseURL}/api/v2/reviews/factor-reviews/${sessionId.value}/${factorKey}?limit=5`)
      
      if (response.status === 501) {
        loading.value = false
        stopLoadingTimer()
        
        pushBot(
          `"${displayName}"에 대한 상세 리뷰 분석 기능은 현재 준비 중입니다.<br />다른 후회 포인트를 선택하거나 궁금한 점을 질문해 주세요.`,
          null,
          null,
          null,
          'alert'
        )
        return
      }
      
      const data = await response.json()
      
      if (data.reviews && data.reviews.length > 0) {
        const reviewsArray = data.reviews.map(r => ({
          text: Array.isArray(r.sentences) ? r.sentences.join(' ') : r.sentences,
          rating: r.rating
        }))
        
        let message = `"${displayName}"와 관련된 리뷰를`
        if (data.anchor_terms && Object.keys(data.anchor_terms).length > 0) {
          const anchorSummary = Object.entries(data.anchor_terms)
            .map(([term, count]) => `'${term}' ${count}건`)
            .join(', ')
          message = `"${displayName}"와 관련된 리뷰를 ${anchorSummary}을 찾았어요.`
        } else {
          message = `"${displayName}"와 관련된 리뷰를 찾았어요.`
        }
        
        pushBot(
          message,
          null,
          null,
          reviewsArray,
          null,
          null
        )
        
        if (data.questions && data.questions.length > 0) {
          const question = data.questions[0]
          pushBot(
            question.question_text,
            question.choices || null,
            null,
            null,
            null,
            null,
            question.question_id,
            factorKey
          )
        }
      } else {
        pushBot(`"${displayName}"와 관련된 리뷰를 찾지 못했습니다.`, null, null, null, 'alert')
      }
      
    } catch (e) {
      console.error('리뷰 조회 오류:', e)
      pushBot(
        `"${displayName}"에 대한 리뷰를 불러오는 중 오류가 발생했어요.`,
        null,
        null,
        null,
        'error'
      )
    } finally {
      loading.value = false
      stopLoadingTimer()
    }
  }

  const selectOption = async (opt) => {
    pushUser(opt)
    
    loading.value = true
    startLoadingTimer()
    loadingType.value = 'search'
    loadingText.value = '답변을 처리 중이에요...'
    
    try {
      const lastBotMessage = messages.value[messages.value.length - 2]
      const questionId = lastBotMessage?.questionId
      const factorKey = lastBotMessage?.factorKey
      
      console.log('=== selectOption DEBUG ===')
      console.log('lastMessage:', lastBotMessage)
      console.log('questionId:', questionId)
      console.log('factorKey:', factorKey)
      console.log('answer:', opt)
      
      const response = await fetch(
        `${config.baseURL}/api/v2/reviews/answer-question/${sessionId.value}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            answer: opt,
            question_id: questionId,
            factor_key: factorKey
          })
        }
      )
      
      const data = await response.json()
      console.log('answer-question response:', data)
      
      if (!response.ok || data.detail) {
        console.error('API 에러:', data)
        pushBot(
          `질문 답변 처리 중 오류가 발생했어요.<br/>에러: ${JSON.stringify(data.detail || data)}`,
          null,
          null,
          null,
          'error'
        )
        loading.value = false
        stopLoadingTimer()
        return
      }
      
      if (data.is_converged && data.analysis) {
        if (data.analysis.top_factors && Array.isArray(data.analysis.top_factors)) {
          data.analysis.top_factors.forEach(factor => {
            if (factor.factor_key && factor.display_name) {
              factorsMap.value[factor.factor_key] = factor.display_name
            }
          })
          console.log('[factorsMap 구성 완료-selectOption]', factorsMap.value)
        }
        
        loadingType.value = 'analyze'
        loadingText.value = '후회 포인트를 분석 중이에요...'
        
        await new Promise(r => setTimeout(r, 800))
        
        if (data.analysis.llm_summaries && data.analysis.llm_summaries.length > 1) {
          console.log('[다중 전략] 전략 개수:', data.analysis.llm_summaries.length)
          
          for (const strategyResult of data.analysis.llm_summaries) {
            const llmSummary = strategyResult.summary
            const strategyName = strategyResult.strategy
            const strategyNameKo = getStrategyNameInKorean(strategyName)
            const responseFile = strategyResult.response_file
            
            try {
              const cleanedJson = cleanJsonString(llmSummary)
              const analysisJson = JSON.parse(cleanedJson)
              
              replaceFactorKeysWithDisplayNames(analysisJson)
              
              pushBot(
                null,
                null, null, null, 'analyze',
                null, null, null, false, null, null,
                {
                  productName: data.analysis.product_name || '제품',
                  strategyName: strategyNameKo,
                  summary: analysisJson.summary,
                  key_findings: analysisJson.key_findings,
                  balanced_view: analysisJson.balanced_view,
                  decision_rule: analysisJson.decision_rule,
                  final_recommendation: analysisJson.final_recommendation,
                  one_line_tip: analysisJson.one_line_tip
                }
              )
              
              console.log(`[별점 요청-selectOption] strategy=${strategyName}, responseFile=${responseFile}`)
              
              pushBot(
                `"${strategyNameKo}" 분석에 만족하셨나요? 별점을 남겨주세요!`, 
                null, null, null, null, null, null, null, 
                true,
                responseFile,
                strategyName
              )
            } catch (e) {
              console.error(`[${strategyName}] 분석 결과 파싱 실패:`, e)
              const htmlContent = convertMarkdownToHtml(llmSummary)
              pushBot(htmlContent, null, null, null, 'analyze')
            }
          }
          
          console.log('[다중 전략-selectOption] 모든 전략 처리 완료')
          
          waitingForNewAnalysisResponse.value = true
          pushBot('다른 상품에 대한 리뷰를 분석해 드릴까요?')
          loading.value = false
          stopLoadingTimer()
          return
        }
        
        const llmSummary = data.analysis.llm_summary
        
        if (llmSummary) {
          try {
            const cleanedJson = cleanJsonString(llmSummary)
            const analysisJson = JSON.parse(cleanedJson)
            
            replaceFactorKeysWithDisplayNames(analysisJson)
            
            pushBot(
              null,
              null, null, null, 'analyze',
              null, null, null, false, null, null,
              {
                productName: data.analysis.product_name || '제품',
                strategyName: null,
                summary: analysisJson.summary,
                key_findings: analysisJson.key_findings,
                balanced_view: analysisJson.balanced_view,
                decision_rule: analysisJson.decision_rule,
                final_recommendation: analysisJson.final_recommendation,
                one_line_tip: analysisJson.one_line_tip
              }
            )
            
            const responseFile = data.analysis.response_file || `llm_response_${Date.now()}.json`
            pushBot(
              '분석 결과에 만족하셨나요? 별점을 남겨주세요!', 
              null, null, null, null, null, null, null, 
              true,
              responseFile
            )
            
          } catch (e) {
            console.error('LLM 분석 결과 파싱 실패:', e)
            const htmlContent = convertMarkdownToHtml(llmSummary)
            pushBot(htmlContent, null, null, null, 'analyze')
            
            const responseFile = data.analysis.response_file || `llm_response_${Date.now()}.json`
            pushBot(
              '분석 결과에 만족하셨나요? 별점을 남겨주세요!', 
              null, null, null, null, null, null, null, 
              true,
              responseFile
            )
          }
        } else {
          pushBot('분석이 완료되었습니다.', null, null, null, 'analyze')
        }
      } else if (data.next_question) {
        if (data.related_reviews && data.related_reviews.length > 0) {
          const reviewsArray = data.related_reviews.map(r => ({
            text: r.text,
            rating: r.rating
          }))
          
          const message = data.review_message || `관련 리뷰를 찾았어요.`
          
          pushBot(
            message,
            null,
            null,
            reviewsArray
          )
        }
        
        pushBot(
          data.next_question.question_text,
          data.next_question.choices || null,
          null,
          null,
          null,
          null,
          data.next_question.question_id,
          data.next_question.factor_key
        )
      } else {
        pushBot('질문이 종료되었습니다.', null, null, null, 'alert')
      }
    } catch (e) {
      console.error('질문 답변 처리 오류:', e)
      pushBot('답변을 처리하는 중 오류가 발생했어요.', null, null, null, 'error')
    } finally {
      loading.value = false
      stopLoadingTimer()
    }
  }

  const clearConversation = async () => {
    if (!sessionId.value) return
    
    try {
      await resetSession(sessionId.value)
      
      let analyzeMessageIndex = -1
      for (let i = 0; i < messages.value.length; i++) {
        if (messages.value[i].messageType === 'analyze' && messages.value[i].regretPoints) {
          analyzeMessageIndex = i
          break
        }
      }
      
      if (analyzeMessageIndex !== -1) {
        messages.value = messages.value.slice(0, analyzeMessageIndex + 1)
      } else {
        const userInputIndex = messages.value.findIndex(msg => msg.role === 'user')
        if (userInputIndex !== -1) {
          messages.value = messages.value.slice(0, userInputIndex + 1)
        }
      }
      
      scrollBottom()
    } catch (error) {
      console.error('세션 재분석 실패:', error)
      let analyzeMessageIndex = -1
      for (let i = 0; i < messages.value.length; i++) {
        if (messages.value[i].messageType === 'analyze' && messages.value[i].regretPoints) {
          analyzeMessageIndex = i
          break
        }
      }
      
      if (analyzeMessageIndex !== -1) {
        messages.value = messages.value.slice(0, analyzeMessageIndex + 1)
      } else {
        const userInputIndex = messages.value.findIndex(msg => msg.role === 'user')
        if (userInputIndex !== -1) {
          messages.value = messages.value.slice(0, userInputIndex + 1)
        }
      }
    }
  }

  const startNewAnalysis = () => {
    messages.value = []
    sessionId.value = null
    
    if (useProductSelection.value) {
      analysisMode.value = 'product'
    } else {
      analysisMode.value = null
    }
    
    scrollBottom()
  }

  const handleUrlAnalysis = async (url) => {
    loading.value = true
    startLoadingTimer()
    loadingType.value = 'search'
    loadingText.value = '상품 리뷰를 수집 중이에요...'
    
    try {
      const res = await startSession(url)
      sessionId.value = res.session_id      
      console.log('세션 생성 완료:', res.session_id)
      console.log('suggested_factors:', res.suggested_factors)
      
      loadingType.value = 'analyze'
      loadingText.value = '후회 포인트를 분석 중이에요...'
      await new Promise(r => setTimeout(r, 800))

      const productName = res.product_name || '이 상품'
      const reviewCount = res.total_count || 0
      pushBot(
        `<span style="color: #017FFF; font-weight: 400;">${productName}</span>의<br />별점 낮은 순으로 ${reviewCount}건에서 후회 포인트를 분석해 보았어요.<br />
아래 키워드를 선택하면 해당 리뷰 키워드와 관련된 리뷰를 보여드릴께요.<br />
혹은 궁금하신 점을 질문해 주시면 관련해서 자세히 설명 드릴께요.`,
        null,
        res.suggested_factors,
        null,
        'analyze'
      )
    } catch (e) {
      const error_prefix = loadingType.value === 'search' ? '리뷰 수집 중' : '후회 포인트 분석 중'
      
      if(loadingType.value === 'search') {
        loadingType.value = 'error'
        loadingText.value = '리뷰 수집에 실패했어요.'
      } else {
        loadingType.value = 'error'
        loadingText.value = '후회 포인트 분석에 실패했어요.'
      }
      await new Promise(r => setTimeout(r, 1000))

      pushBot(
        `${error_prefix} 오류가 발생했어요.`,
        null,
        null,
        null,
        'error'
      )
      pushBot(
        `<strong>ReviewLens</strong>에서 지원하지 않는 URL이거나<br />
         리뷰 수집에 실패했어요. 다른 URL을 입력해 주세요.`,
        null,
        null,
        null,
        'alert'
      )
      sessionId.value = null
      analysisMode.value = null
    } finally {
      loading.value = false
      stopLoadingTimer()
    }
  }

  return {
    // State
    messages,
    input,
    loading,
    loadingText,
    loadingType,
    scrollRef,
    loadingElapsedSeconds,
    sessionId,
    availableProducts,
    analysisMode,
    useProductSelection,
    welcomeMessage,
    strategyNames,
    factorsMap,
    
    // Methods
    formatTimestamp,
    getRiskLabel,
    getLoadingIcon,
    getMessageIcon,
    showProductSelection,
    showUrlInput,
    selectProduct,
    send,
    selectRegretPoint,
    selectOption,
    submitRating,
    clearConversation,
    startNewAnalysis
  }
}
