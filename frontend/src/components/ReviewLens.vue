<template>
  <div class="chat-page">
    <!-- Top Header (Fixed) -->
    <header class="top-header">
      <h1>후회 포인트 분석<br/></h1>
      <p>부정 리뷰 기반 구매가이드</p>
    </header>

    <!-- Chat body -->
    <section class="chat-body" ref="scrollRef">
      <!-- Greeting (Scrollable) -->
      <div class="greeting">
        <img src="/images/ic_main.png" alt="ReviewLens Logo" class="logo" />
        <h3>안녕하세요!<br />
          후회 없는 구매를 위한 리뷰 분석 서비스<br />
          <p>ReviewLens</p> 입니다.
        </h3>
      </div>

      <!-- Welcome (항상 표시) -->
      <div class="message bot welcome">
        <div class="bubble-wrapper">
          <div class="bubble">
            <p class="hint">
              {{ welcomeMessage }}<br />
              <small>부정적인 리뷰만 분석합니다</small>
            </p>
            <!-- 초기 선택 옵션 (URL 모드일 때만 표시) -->
            <div v-if="!useProductSelection && !analysisMode" class="option-list">
              <button @click="showProductSelection">
                📋 상품 목록에서 선택하기
              </button>
              <button @click="showUrlInput">
                🔗 URL 직접 입력하기
              </button>
            </div>
            <!-- 상품 선택 버튼 -->
            <div v-if="(useProductSelection || analysisMode === 'product') && availableProducts.length > 0" class="option-list">
              <button
                v-for="product in availableProducts"
                :key="product.product_id || product"
                @click="selectProduct(typeof product === 'string' ? product : product.product_name)"
              >
                <div v-if="typeof product === 'object'" style="text-align: left;">
                  <div style="font-weight: 600;">{{ product.product_name }}</div>
                  <!-- <div style="font-size: 12px; color: #8e8e93; margin-top: 2px;">
                    {{ product.category }} · 리뷰 {{ product.review_count }}건
                  </div> -->
                </div>
                <span v-else>{{ product }}</span>
              </button>
            </div>
            <!-- URL 입력 안내 -->
            <p v-if="analysisMode === 'url'" class="hint" style="margin-top: 12px;">
              상품 URL을 입력창에 입력해주세요.
            </p>
          </div>
          <div class="timestamp">{{ formatTimestamp() }}</div>
        </div>
      </div>

      <!-- Messages -->
      <div v-for="(msg, idx) in messages" :key="idx" :class="['message', msg.role]">
        <div class="bubble-wrapper">
          <div class="bubble" :class="msg.messageType">
            <!-- 메시지 텍스트 먼저 표시 -->
            <div v-if="msg.messageType" class="message-with-icon">
              <img :src="getMessageIcon(msg.messageType)" alt="아이콘" class="message-icon" />
              <div v-html="msg.text"></div>
            </div>
            <p v-else-if="msg.text" v-html="msg.text"></p>

            <!-- 리뷰 근거 출력 (메시지 다음) -->
            <div v-if="msg.reviews" class="reviews-evidence">
              <div class="evidence-title">
                <span v-if="msg.reviewSummary">{{ msg.reviewSummary }}</span>
              </div>
              <div
                v-for="(review, rIdx) in msg.reviews"
                :key="rIdx"
                class="review-item"
              >
                <div class="message-with-icon">
                  <img src="/images/ic_review.png" alt="아이콘" class="message-icon" />
                  <div class="review-text">{{ review.text }}</div>
                </div>
              </div>
            </div>

            <!-- 후회 포인트 버튼 -->
            <div v-if="msg.regretPoints" class="option-list">
              <button
                v-for="factor in msg.regretPoints"
                :key="factor.factor_key || factor"
                @click="selectRegretPoint(typeof factor === 'object' ? factor.factor_key : factor)"
              >
                {{ typeof factor === 'object' ? factor.display_name : factor }}
              </button>
            </div>

            <!-- 별점 선택 UI -->
            <div v-if="msg.showRating" class="rating-container">
              <div class="rating-stars">
                <span
                  v-for="star in 5"
                  :key="star"
                  class="star"
                  :class="{ filled: star <= (msg.hoverRating || 0) }"
                  @mouseenter="msg.hoverRating = star"
                  @mouseleave="msg.hoverRating = 0"
                  @click="submitRating(star, msg.responseFile, msg.strategy)"
                >
                  ⭐
                </span>
              </div>
            </div>

            <!-- 일반 옵션 버튼 -->
            <div v-if="msg.options" class="option-list">
              <button
                v-for="(opt, optIdx) in msg.options"
                :key="`opt-${optIdx}-${opt}`"
                @click="selectOption(opt)"
              >
                {{ opt }}
              </button>
            </div>
          </div>
          <div class="timestamp">{{ msg.timestamp }}</div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="message bot">
        <div class="bubble-wrapper">
          <div class="bubble loading-bubble" :class="loadingType">
            <img :src="getLoadingIcon()" alt="아이콘" class="loading-icon" />
            <span>{{ loadingText }}</span>
          </div>
          <div class="timestamp">{{ loadingElapsedSeconds }}초 경과</div>
        </div>
      </div>
    </section>

    <!-- Action Buttons (세션이 있을 때만 표시) -->
    <div v-if="sessionId" class="action-buttons">
      <button @click="clearConversation" class="action-btn clear-btn" :disabled="loading">
        <span><img src="/images/ic_rotate-cw.png" alt="재분석" class="action-icon" /> 상품 재분석</span>
      </button>
      <button @click="startNewAnalysis" class="action-btn new-btn" :disabled="loading">
        <span><img src="/images/ic_trash.png" alt="분석" class="action-icon" /> 분석 초기화</span>
      </button>
    </div>

    <!-- Input -->
    <footer class="input-area">
      <div class="input-wrapper">
        <input
          v-model="input"
          @keyup.enter="send"
          placeholder="궁금한 점을 질문해 주세요."
          :disabled="loading"
        />
        <button @click="send" class="send-btn" :disabled="loading">
          <img 
            :src="input.trim().length > 0 && !loading ? '/images/ic_input_active.png' : '/images/ic_input_default.png'" 
            alt="전송"
          />
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, computed } from 'vue'
import { startSession, sendMessage, resetSession, getProducts, analyzeProduct, getAppConfig } from '../api/chat.js'
import { marked } from 'marked'

// Marked 옵션 설정
marked.setOptions({
  breaks: true, // 줄바꿈을 <br>로 변환
  gfm: true // GitHub Flavored Markdown 사용
})

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

// 환영 메시지 (설정에 따라 변경)
const welcomeMessage = computed(() => {
  if (useProductSelection.value) {
    return '아래의 상품 중 분석할 상품을 선택해 주세요.'
  } else {
    return '제가 분석할 상품을 선택하거나 URL을 입력해주세요.'
  }
})

// 컴포넌트 마운트 시 설정 로드
onMounted(async () => {
  try {
    // 앱 설정 로드
    const config = await getAppConfig()
    useProductSelection.value = config.use_product_selection
    
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

// 상품 선택 모드 활성화
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

// URL 입력 모드 활성화
const showUrlInput = () => {
  analysisMode.value = 'url'
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

const pushBot = (text, options = null, regretPoints = null, reviews = null, messageType = null, reviewSummary = null, questionId = null, factorKey = null, showRating = false, responseFile = null, strategy = null) => {
  messages.value.push({ 
    role: 'bot', 
    text, 
    options, 
    regretPoints, 
    reviews,
    messageType,
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
  
  // 별점이 있으면 별 표시 추가
  if (rating) {
    userMsg.text = '⭐'.repeat(rating) + ` (${rating}점)`
  }
  
  messages.value.push(userMsg)
  scrollBottom()
}

// 별점 제출
const submitRating = async (rating, responseFile, strategy = null) => {
  try {
    // 사용자 메시지에 별점 표시
    pushUser('', rating)
    
    // 별점 요청 메시지의 별점 UI 숨기기
    const lastBotMessage = [...messages.value].reverse().find(m => m.role === 'bot' && m.showRating)
    if (lastBotMessage) {
      lastBotMessage.showRating = false
    }
    
    // strategy 파라미터가 없으면 lastBotMessage에서 가져오기
    const strategyToSend = strategy || lastBotMessage?.strategy
    
    console.log('별점 전송:', { responseFile, rating, strategy: strategyToSend })
    
    // 백엔드로 별점 전송
    const payload = {
      response_file: responseFile,
      rating: rating
    }
    
    // strategy가 있으면 추가
    if (strategyToSend) {
      payload.strategy = strategyToSend
    }
    
    const response = await fetch('http://localhost:8000/api/v2/reviews/rate-response', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
    
    if (response.ok) {
      console.log('별점 전송 성공:', rating)
      
      // 다중 전략이 아니면 "다른 상품 분석?" 메시지 표시
      if (!strategyToSend || messages.value.filter(m => m.showRating).length === 0) {
        pushBot('소중한 의견 감사합니다! 😊<br/>다른 상품도 분석해 드릴까요?')
        waitingForNewAnalysisResponse.value = true
      } else {
        pushBot('감사합니다! 😊')
      }
    } else {
      const errorData = await response.json()
      console.error('별점 전송 실패:', response.status, errorData)
      pushBot(`평가를 저장하는데 실패했어요. 😢<br/>오류: ${errorData.detail || '알 수 없는 오류'}`)
    }
  } catch (error) {
    console.error('별점 전송 오류:', error)
    pushBot('평가를 저장하는데 실패했어요. 😢<br/>네트워크 오류가 발생했습니다.')
  }
}

const pushUser_old = (text) => {
  messages.value.push({ 
    role: 'user', 
    text,
    timestamp: formatTimestamp()
  })
  scrollBottom()
}

/** 상품 선택 시 리뷰 분석 시작 */
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
    
    // 분석 상태 메시지
    loadingType.value = 'analyze'
    loadingText.value = '후회 포인트를 분석 중이에요...'
    await new Promise(r => setTimeout(r, 800))
    
    // 후회 포인트 버튼 출력
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

/** 최초 URL 입력 또는 추가 질문 */
const send = async () => {
  if (!input.value.trim()) return

  const text = input.value
  input.value = ''
  
  // "다른 상품 분석?" 질문에 대한 답변 처리
  if (waitingForNewAnalysisResponse.value) {
    pushUser(text)
    waitingForNewAnalysisResponse.value = false
    
    // 긍정 답변 감지
    const positivePatterns = /^(네|yes|응|예|ㅇㅇ|ㅇ|ok|okay|좋아|그래|맞아|분석|새로|다른|할게|할래|해줘|부탁|원해)/i
    // 부정 답변 감지
    const negativePatterns = /^(아니|no|노|ㄴㄴ|ㄴ|싫어|안|됐어|됐|괜찮|필요없|그만|재분석|다시|처음)/i
    
    if (positivePatterns.test(text.trim())) {
      // 긍정: 분석 초기화 (새로운 상품 분석)
      pushBot('알겠습니다! 새로운 상품을 분석해드릴게요. 상품을 선택해주세요. ✨')
      startNewAnalysis()
      return
    } else if (negativePatterns.test(text.trim())) {
      // 부정: 상품 재분석 (같은 상품, 대화만 초기화)
      pushBot('알겠습니다! 같은 상품으로 처음부터 다시 시작할게요. 🔄')
      await clearConversation()
      return
    } else {
      // 애매한 답변: 다시 물어보기
      waitingForNewAnalysisResponse.value = true
      pushBot('"네" 또는 "아니오"로 답변해주세요. 다른 상품을 분석하시겠어요?')
      return
    }
  }
  
  // URL 패턴 확인 (http:// 또는 https://로 시작하거나 일반적인 URL 형태)
  const isUrl = /^https?:\/\/.+/.test(text.trim()) || 
                /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/.test(text.trim())
  
  // URL 입력 모드에서 URL 입력
  if (analysisMode.value === 'url' && isUrl && !sessionId.value) {
    pushUser(text)
    await handleUrlAnalysis(text)
    return
  }
  
  pushUser(text)

  // 세션이 없으면 무시 (상품 선택으로만 세션 생성)
  if (!sessionId.value) {
    pushBot('먼저 위에서 분석할 상품을 선택해 주세요.', null, null, null, 'alert')
    return
  }

  // v2: 자유 텍스트도 answer-question API로 처리
  loading.value = true
  startLoadingTimer()
  loadingType.value = 'search'
  loadingText.value = '답변을 처리 중이에요...'
  
  try {
    // 마지막 메시지에서 question_id와 factor_key 찾기
    const lastMessage = messages.value[messages.value.length - 2] // user 메시지 전
    const questionId = lastMessage?.questionId
    const factorKey = lastMessage?.factorKey
    
    // answer-question API 호출
    const response = await fetch(
      `http://localhost:8000/api/v2/reviews/answer-question/${sessionId.value}`,
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
    
    // 수렴 여부 확인
    if (data.is_converged && data.analysis) {
      loadingType.value = 'analyze'
      loadingText.value = '후회 포인트를 분석 중이에요...'
      await new Promise(r => setTimeout(r, 800))
      
      // 다중 전략인 경우
      if (data.analysis.llm_summaries && data.analysis.llm_summaries.length > 1) {
        console.log('[다중 전략] 전략 개수:', data.analysis.llm_summaries.length)
        
        for (const strategyResult of data.analysis.llm_summaries) {
          const llmSummary = strategyResult.summary
          const strategyName = strategyResult.strategy
          const responseFile = strategyResult.response_file
          
          try {
            const analysisJson = JSON.parse(llmSummary)
            let markdown = `# 📊 ${data.analysis.product_name || '제품'} 분석 결과 (${strategyName} 스타일)\n\n`
            
            if (analysisJson.summary) {
              markdown += `## 💡 요약\n${analysisJson.summary}\n\n`
            }
            
            if (analysisJson.key_findings && analysisJson.key_findings.length > 0) {
              markdown += `## 🔍 주요 발견사항\n\n`
              analysisJson.key_findings.forEach((finding, idx) => {
                const riskEmoji = finding.risk_level === 'high' ? '🔴' : finding.risk_level === 'mid' ? '🟡' : '🟢'
                markdown += `### ${idx + 1}. ${finding.factor} ${riskEmoji}\n${finding.what_users_say}\n\n`
              })
            }
            
            if (analysisJson.balanced_view) {
              markdown += `## ⚖️ 균형잡힌 시각\n\n`
              if (analysisJson.balanced_view.pros && analysisJson.balanced_view.pros.length > 0) {
                markdown += `### ✅ 장점\n`
                analysisJson.balanced_view.pros.forEach(pro => { markdown += `- ${pro.point}\n` })
                markdown += `\n`
              }
              if (analysisJson.balanced_view.cons && analysisJson.balanced_view.cons.length > 0) {
                markdown += `### ⚠️ 단점/주의사항\n`
                analysisJson.balanced_view.cons.forEach(con => { markdown += `- ${con.point}\n` })
                markdown += `\n`
              }
              if (analysisJson.balanced_view.mixed && analysisJson.balanced_view.mixed.length > 0) {
                markdown += `### 🔄 상황에 따라 다름\n`
                analysisJson.balanced_view.mixed.forEach(mix => { markdown += `- ${mix.point}\n` })
                markdown += `\n`
              }
            }
            
            if (analysisJson.decision_rule) {
              markdown += `## 🤔 구매 결정 가이드\n\n`
              if (analysisJson.decision_rule.if_buy && analysisJson.decision_rule.if_buy.length > 0) {
                markdown += `### 구매를 고려해도 좋은 경우:\n`
                analysisJson.decision_rule.if_buy.forEach(condition => { markdown += `- ${condition}\n` })
                markdown += `\n`
              }
              if (analysisJson.decision_rule.if_hold && analysisJson.decision_rule.if_hold.length > 0) {
                markdown += `### 보류가 나은 경우:\n`
                analysisJson.decision_rule.if_hold.forEach(condition => { markdown += `- ${condition}\n` })
                markdown += `\n`
              }
            }
            
            if (analysisJson.final_recommendation) {
              const recEmoji = analysisJson.final_recommendation === '구매' ? '✅' : 
                             analysisJson.final_recommendation === '보류' ? '⏸️' : '🔍'
              markdown += `## ${recEmoji} 최종 추천: ${analysisJson.final_recommendation}\n\n`
            }
            
            if (analysisJson.one_line_tip) {
              markdown += `> 💬 **Tip:** ${analysisJson.one_line_tip}\n\n`
            }
            
            const htmlContent = convertMarkdownToHtml(markdown)
            pushBot(htmlContent, null, null, null, 'analyze')
            
            console.log(`[별점 요청] strategy=${strategyName}, responseFile=${responseFile}`)
            
            // 각 전략별 별점 요청
            pushBot(
              `"${strategyName}" 스타일 분석에 만족하셨나요? 별점을 남겨주세요!`, 
              null, null, null, null, null, null, null, 
              true,  // showRating
              responseFile,
              strategyName  // strategy
            )
          } catch (e) {
            console.error(`[${strategyName}] 분석 결과 파싱 실패:`, e)
            const htmlContent = convertMarkdownToHtml(llmSummary)
            pushBot(htmlContent, null, null, null, 'analyze')
          }
        }
        
        console.log('[다중 전략] 모든 전략 처리 완료')
        
        // 다중 전략 완료 후 다음 분석 안내
        waitingForNewAnalysisResponse.value = true
        pushBot('다른 상품에 대한 리뷰를 분석해 드릴까요?')
        loading.value = false
        stopLoadingTimer()
        return
      }
      
      // 단일 전략인 경우
      const llmSummary = data.analysis.llm_summary
      if (llmSummary) {
        try {
          const analysisJson = JSON.parse(llmSummary)
          let markdown = `# 📊 ${data.analysis.product_name || '제품'} 분석 결과\n\n`
          
          if (analysisJson.summary) {
            markdown += `## 💡 요약\n${analysisJson.summary}\n\n`
          }
          
          if (analysisJson.key_findings && analysisJson.key_findings.length > 0) {
            markdown += `## 🔍 주요 발견사항\n\n`
            analysisJson.key_findings.forEach((finding, idx) => {
              const riskEmoji = finding.risk_level === 'high' ? '🔴' : finding.risk_level === 'mid' ? '🟡' : '🟢'
              markdown += `### ${idx + 1}. ${finding.factor} ${riskEmoji}\n${finding.what_users_say}\n\n`
            })
          }
          
          if (analysisJson.balanced_view) {
            markdown += `## ⚖️ 균형잡힌 시각\n\n`
            if (analysisJson.balanced_view.pros && analysisJson.balanced_view.pros.length > 0) {
              markdown += `### ✅ 장점\n`
              analysisJson.balanced_view.pros.forEach(pro => { markdown += `- ${pro.point}\n` })
              markdown += `\n`
            }
            if (analysisJson.balanced_view.cons && analysisJson.balanced_view.cons.length > 0) {
              markdown += `### ⚠️ 단점/주의사항\n`
              analysisJson.balanced_view.cons.forEach(con => { markdown += `- ${con.point}\n` })
              markdown += `\n`
            }
            if (analysisJson.balanced_view.mixed && analysisJson.balanced_view.mixed.length > 0) {
              markdown += `### 🔄 상황에 따라 다름\n`
              analysisJson.balanced_view.mixed.forEach(mix => { markdown += `- ${mix.point}\n` })
              markdown += `\n`
            }
          }
          
          if (analysisJson.decision_rule) {
            markdown += `## 🤔 구매 결정 가이드\n\n`
            if (analysisJson.decision_rule.if_buy && analysisJson.decision_rule.if_buy.length > 0) {
              markdown += `### 구매를 고려해도 좋은 경우:\n`
              analysisJson.decision_rule.if_buy.forEach(condition => { markdown += `- ${condition}\n` })
              markdown += `\n`
            }
            if (analysisJson.decision_rule.if_hold && analysisJson.decision_rule.if_hold.length > 0) {
              markdown += `### 보류가 나은 경우:\n`
              analysisJson.decision_rule.if_hold.forEach(condition => { markdown += `- ${condition}\n` })
              markdown += `\n`
            }
          }
          
          if (analysisJson.final_recommendation) {
            const recEmoji = analysisJson.final_recommendation === '구매' ? '✅' : 
                           analysisJson.final_recommendation === '보류' ? '⏸️' : '🔍'
            markdown += `## ${recEmoji} 최종 추천: ${analysisJson.final_recommendation}\n\n`
          }
          
          if (analysisJson.one_line_tip) {
            markdown += `> 💬 **Tip:** ${analysisJson.one_line_tip}\n\n`
          }
          
          const htmlContent = convertMarkdownToHtml(markdown)
          pushBot(htmlContent, null, null, null, 'analyze')
          
          // 별점 요청 메시지 추가
          const responseFile = data.analysis.response_file || `llm_response_${Date.now()}.json`
          pushBot(
            '분석 결과에 만족하셨나요? 별점을 남겨주세요!', 
            null, null, null, null, null, null, null, 
            true,  // showRating
            responseFile
          )
        } catch (e) {
          console.error('LLM 분석 결과 파싱 실패:', e)
          const htmlContent = convertMarkdownToHtml(llmSummary)
          pushBot(htmlContent, null, null, null, 'analyze')
          
          // 별점 요청 메시지 추가
          const responseFile = data.analysis.response_file || `llm_response_${Date.now()}.json`
          pushBot(
            '분석 결과에 만족하셨나요? 별점을 남겨주세요!', 
            null, null, null, null, null, null, null, 
            true,  // showRating
            responseFile
          )
        }
      } else {
        pushBot('분석이 완료되었습니다.', null, null, null, 'analyze')
      }
      
      // 별점 요청 후에는 "다른 상품 분석?" 메시지를 제거
      // waitingForNewAnalysisResponse.value = true
      // pushBot('다른 상품에 대한 리뷰를 분석해 드릴까요?')
    } else if (data.next_question) {
      // 다음 질문 표시
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

/** 4. 후회 포인트 선택 시 리뷰 조회 */
const selectRegretPoint = async (factorKey) => {
  // factor_key를 받았지만, 사용자 메시지는 display_name으로 표시하기 위해
  // regretPoints에서 해당 factor 찾기
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
    // TODO: v2 API 호출 - 현재는 501 Not Implemented
    const response = await fetch(`http://localhost:8000/api/v2/reviews/factor-reviews/${sessionId.value}/${factorKey}?limit=5`)
    
    if (response.status === 501) {
      // 아직 구현 안 됨
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
    
    // 리뷰 표시
    if (data.reviews && data.reviews.length > 0) {
      const reviewsArray = data.reviews.map(r => ({
        text: Array.isArray(r.sentences) ? r.sentences.join(' ') : r.sentences,
        rating: r.rating
      }))
      
      // anchor_terms를 메시지에 통합
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
      
      // 질문이 있으면 추가
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
          factorKey  // 현재 factor_key 저장
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
    // 마지막 bot 메시지에서 question_id와 factor_key 찾기
    // user 메시지를 방금 추가했으므로, 그 이전의 bot 메시지는 length - 2
    const lastBotMessage = messages.value[messages.value.length - 2]
    const questionId = lastBotMessage?.questionId
    const factorKey = lastBotMessage?.factorKey
    
    console.log('=== selectOption DEBUG ===')
    console.log('lastMessage:', lastBotMessage)
    console.log('questionId:', questionId)
    console.log('factorKey:', factorKey)
    console.log('answer:', opt)
    
    // answer-question API 호출
    const response = await fetch(
      `http://localhost:8000/api/v2/reviews/answer-question/${sessionId.value}`,
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
    
    // 422 에러 또는 에러 응답 처리
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
    
    // 수렴 조건 달성 여부 확인
    if (data.is_converged && data.analysis) {
      // loading 메시지를 "분석 중"으로 변경
      loadingType.value = 'analyze'
      loadingText.value = '후회 포인트를 분석 중이에요...'
      
      // 잠시 대기 (사용자가 메시지 볼 수 있도록)
      await new Promise(r => setTimeout(r, 800))
      
      // 다중 전략인 경우
      if (data.analysis.llm_summaries && data.analysis.llm_summaries.length > 1) {
        console.log('[다중 전략] 전략 개수:', data.analysis.llm_summaries.length)
        
        for (const strategyResult of data.analysis.llm_summaries) {
          const llmSummary = strategyResult.summary
          const strategyName = strategyResult.strategy
          const responseFile = strategyResult.response_file
          
          try {
            const analysisJson = JSON.parse(llmSummary)
            let markdown = `# 📊 ${data.analysis.product_name || '제품'} 분석 결과 (${strategyName} 스타일)\n\n`
            
            if (analysisJson.summary) {
              markdown += `## 💡 요약\n${analysisJson.summary}\n\n`
            }
            
            if (analysisJson.key_findings && analysisJson.key_findings.length > 0) {
              markdown += `## 🔍 주요 발견사항\n\n`
              analysisJson.key_findings.forEach((finding, idx) => {
                const riskEmoji = finding.risk_level === 'high' ? '🔴' : finding.risk_level === 'mid' ? '🟡' : '🟢'
                markdown += `### ${idx + 1}. ${finding.factor} ${riskEmoji}\n${finding.what_users_say}\n\n`
              })
            }
            
            if (analysisJson.balanced_view) {
              markdown += `## ⚖️ 균형잡힌 시각\n\n`
              if (analysisJson.balanced_view.pros && analysisJson.balanced_view.pros.length > 0) {
                markdown += `### ✅ 장점\n`
                analysisJson.balanced_view.pros.forEach(pro => { markdown += `- ${pro.point}\n` })
                markdown += `\n`
              }
              if (analysisJson.balanced_view.cons && analysisJson.balanced_view.cons.length > 0) {
                markdown += `### ⚠️ 단점/주의사항\n`
                analysisJson.balanced_view.cons.forEach(con => { markdown += `- ${con.point}\n` })
                markdown += `\n`
              }
              if (analysisJson.balanced_view.mixed && analysisJson.balanced_view.mixed.length > 0) {
                markdown += `### 🔄 상황에 따라 다름\n`
                analysisJson.balanced_view.mixed.forEach(mix => { markdown += `- ${mix.point}\n` })
                markdown += `\n`
              }
            }
            
            if (analysisJson.decision_rule) {
              markdown += `## 🤔 구매 결정 가이드\n\n`
              if (analysisJson.decision_rule.if_buy && analysisJson.decision_rule.if_buy.length > 0) {
                markdown += `### 구매를 고려해도 좋은 경우:\n`
                analysisJson.decision_rule.if_buy.forEach(condition => { markdown += `- ${condition}\n` })
                markdown += `\n`
              }
              if (analysisJson.decision_rule.if_hold && analysisJson.decision_rule.if_hold.length > 0) {
                markdown += `### 보류가 나은 경우:\n`
                analysisJson.decision_rule.if_hold.forEach(condition => { markdown += `- ${condition}\n` })
                markdown += `\n`
              }
            }
            
            if (analysisJson.final_recommendation) {
              const recEmoji = analysisJson.final_recommendation === '구매' ? '✅' : 
                             analysisJson.final_recommendation === '보류' ? '⏸️' : '🔍'
              markdown += `## ${recEmoji} 최종 추천: ${analysisJson.final_recommendation}\n\n`
            }
            
            if (analysisJson.one_line_tip) {
              markdown += `> 💬 **Tip:** ${analysisJson.one_line_tip}\n\n`
            }
            
            const htmlContent = convertMarkdownToHtml(markdown)
            pushBot(htmlContent, null, null, null, 'analyze')
            
            console.log(`[별점 요청-selectOption] strategy=${strategyName}, responseFile=${responseFile}`)
            
            // 각 전략별 별점 요청
            pushBot(
              `"${strategyName}" 스타일 분석에 만족하셨나요? 별점을 남겨주세요!`, 
              null, null, null, null, null, null, null, 
              true,  // showRating
              responseFile,
              strategyName  // strategy
            )
          } catch (e) {
            console.error(`[${strategyName}] 분석 결과 파싱 실패:`, e)
            const htmlContent = convertMarkdownToHtml(llmSummary)
            pushBot(htmlContent, null, null, null, 'analyze')
          }
        }
        
        console.log('[다중 전략-selectOption] 모든 전략 처리 완료')
        
        // 다중 전략 완료 후 다음 분석 안내
        waitingForNewAnalysisResponse.value = true
        pushBot('다른 상품에 대한 리뷰를 분석해 드릴까요?')
        loading.value = false
        stopLoadingTimer()
        return
      }
      
      // 단일 전략 - LLM 분석 결과 표시
      const llmSummary = data.analysis.llm_summary
      
      if (llmSummary) {
        // JSON 문자열을 파싱
        try {
          const analysisJson = JSON.parse(llmSummary)
          
          // 분석 결과를 마크다운 형식으로 구성
          let markdown = `# 📊 ${data.analysis.product_name || '제품'} 분석 결과\n\n`
          
          // summary
          if (analysisJson.summary) {
            markdown += `## 💡 요약\n${analysisJson.summary}\n\n`
          }
          
          // key_findings
          if (analysisJson.key_findings && analysisJson.key_findings.length > 0) {
            markdown += `## 🔍 주요 발견사항\n\n`
            analysisJson.key_findings.forEach((finding, idx) => {
              const riskEmoji = finding.risk_level === 'high' ? '🔴' : finding.risk_level === 'mid' ? '🟡' : '🟢'
              markdown += `### ${idx + 1}. ${finding.factor} ${riskEmoji}\n`
              markdown += `${finding.what_users_say}\n\n`
            })
          }
          
          // balanced_view
          if (analysisJson.balanced_view) {
            markdown += `## ⚖️ 균형잡힌 시각\n\n`
            
            if (analysisJson.balanced_view.pros && analysisJson.balanced_view.pros.length > 0) {
              markdown += `### ✅ 장점\n`
              analysisJson.balanced_view.pros.forEach(pro => {
                markdown += `- ${pro.point}\n`
              })
              markdown += `\n`
            }
            
            if (analysisJson.balanced_view.cons && analysisJson.balanced_view.cons.length > 0) {
              markdown += `### ⚠️ 단점/주의사항\n`
              analysisJson.balanced_view.cons.forEach(con => {
                markdown += `- ${con.point}\n`
              })
              markdown += `\n`
            }
            
            if (analysisJson.balanced_view.mixed && analysisJson.balanced_view.mixed.length > 0) {
              markdown += `### 🔄 상황에 따라 다름\n`
              analysisJson.balanced_view.mixed.forEach(mix => {
                markdown += `- ${mix.point}\n`
              })
              markdown += `\n`
            }
          }
          
          // decision_rule
          if (analysisJson.decision_rule) {
            markdown += `## 🤔 구매 결정 가이드\n\n`
            
            if (analysisJson.decision_rule.if_buy && analysisJson.decision_rule.if_buy.length > 0) {
              markdown += `### 구매를 고려해도 좋은 경우:\n`
              analysisJson.decision_rule.if_buy.forEach(condition => {
                markdown += `- ${condition}\n`
              })
              markdown += `\n`
            }
            
            if (analysisJson.decision_rule.if_hold && analysisJson.decision_rule.if_hold.length > 0) {
              markdown += `### 보류가 나은 경우:\n`
              analysisJson.decision_rule.if_hold.forEach(condition => {
                markdown += `- ${condition}\n`
              })
              markdown += `\n`
            }
          }
          
          // final_recommendation
          if (analysisJson.final_recommendation) {
            const recEmoji = analysisJson.final_recommendation === '구매' ? '✅' : 
                           analysisJson.final_recommendation === '보류' ? '⏸️' : '🔍'
            markdown += `## ${recEmoji} 최종 추천: ${analysisJson.final_recommendation}\n\n`
          }
          
          // one_line_tip
          if (analysisJson.one_line_tip) {
            markdown += `> 💬 **Tip:** ${analysisJson.one_line_tip}\n\n`
          }
          
          const htmlContent = convertMarkdownToHtml(markdown)
          pushBot(htmlContent, null, null, null, 'analyze')
          
          // 별점 요청 메시지 추가
          const responseFile = data.analysis.response_file || `llm_response_${Date.now()}.json`
          pushBot(
            '분석 결과에 만족하셨나요? 별점을 남겨주세요!', 
            null, null, null, null, null, null, null, 
            true,  // showRating
            responseFile
          )
          
        } catch (e) {
          console.error('LLM 분석 결과 파싱 실패:', e)
          // fallback: 원본 텍스트 표시
          const htmlContent = convertMarkdownToHtml(llmSummary)
          pushBot(htmlContent, null, null, null, 'analyze')
          
          // 별점 요청 메시지 추가
          const responseFile = data.analysis.response_file || `llm_response_${Date.now()}.json`
          pushBot(
            '분석 결과에 만족하셨나요? 별점을 남겨주세요!', 
            null, null, null, null, null, null, null, 
            true,  // showRating
            responseFile
          )
        }
      } else {
        // llm_summary가 없으면 기본 메시지
        pushBot('분석이 완료되었습니다.', null, null, null, 'analyze')
      }
      
      // 별점 요청 후에는 "다른 상품 분석?" 메시지 제거
      // waitingForNewAnalysisResponse.value = true
      // pushBot('다른 상품에 대한 리뷰를 분석해 드릴까요?')
    } else if (data.next_question) {
      // 관련 리뷰가 있으면 먼저 표시
      if (data.related_reviews && data.related_reviews.length > 0) {
        const reviewsArray = data.related_reviews.map(r => ({
          text: r.text,
          rating: r.rating
        }))
        
        // 백엔드에서 보낸 메시지 사용 (anchor_term별 건수 포함)
        const message = data.review_message || `관련 리뷰를 찾았어요.`
        
        pushBot(
          message,
          null,
          null,
          reviewsArray
        )
      }
      
      // 다음 질문 표시
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

/** 모든 대화 내용 삭제 (분석 결과까지만 남김) */
const clearConversation = async () => {
  if (!sessionId.value) return
  
  try {
    // 백엔드에 세션 재분석 요청
    await resetSession(sessionId.value)
    
    // 첫 번째 분석 결과 메시지(messageType === 'analyze'이고 regretPoints가 있는)의 인덱스를 찾음
    let analyzeMessageIndex = -1
    for (let i = 0; i < messages.value.length; i++) {
      if (messages.value[i].messageType === 'analyze' && messages.value[i].regretPoints) {
        analyzeMessageIndex = i
        break
      }
    }
    
    if (analyzeMessageIndex !== -1) {
      // 첫 번째 분석 결과까지만 남기고 나머지 삭제
      messages.value = messages.value.slice(0, analyzeMessageIndex + 1)
    } else {
      // 분석 결과가 없으면 첫 번째 사용자 메시지(상품 선택)까지만 남김
      const userInputIndex = messages.value.findIndex(msg => msg.role === 'user')
      if (userInputIndex !== -1) {
        messages.value = messages.value.slice(0, userInputIndex + 1)
      }
    }
    
    scrollBottom()
  } catch (error) {
    console.error('세션 재분석 실패:', error)
    // 에러가 발생해도 UI는 초기화
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

/** 다른 상품 분석 시작 (상품 목록 다시 표시) */
const startNewAnalysis = () => {
  // 모든 메시지 삭제
  messages.value = []
  
  // 세션 초기화
  sessionId.value = null
  
  // 분석 모드 복원 (상품 선택 모드 유지)
  if (useProductSelection.value) {
    analysisMode.value = 'product'
  } else {
    analysisMode.value = null
  }
  
  scrollBottom()
}

/** URL 분석 처리 */
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
    
    // 시스템 상태 메시지 (분석 완료)
    loadingType.value = 'analyze'
    loadingText.value = '후회 포인트를 분석 중이에요...'
    await new Promise(r => setTimeout(r, 800))

    // 후회 포인트 버튼 출력
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
    
    // 오류 처리
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
</script>

<style scoped>
* {
  -webkit-tap-highlight-color: transparent;
  -webkit-touch-callout: none;
}

.chat-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fff !important;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif;
  max-width: 480px;
  margin: 0 auto;
  overflow: hidden;
  box-shadow: 0 0 20px rgba(0,0,0,0.1);
}

/* Top Header (Fixed) */
.top-header {
  padding: max(env(safe-area-inset-top), 14px) 20px 14px;
  text-align: left;
  background: var(--Colors-White-100, #FFF);
  /* box-shadow: 0 2px 8px rgba(0,0,0,0.1); */
  position: relative;
  color: var(--Colors-Black-100, #121212);
  /* Global Tokens/Pretendard/subtitle */
  font-family: Pretendard;
  font-size: 0.9rem;/* 14px */
  font-style: normal;
  line-height: 150%; /* 1.5rem */
  letter-spacing: -0.02rem;
  z-index: 10;
}

.top-header h1 {
  margin: 0;
  color: var(--Colors-Black-100, #121212);
  /* Global Tokens/Pretendard/subtitle */
  font-family: Pretendard;
  font-size: 1.15rem;/* 18px */
  font-style: normal;
  font-weight: 700;
  line-height: 150%; /* 1.5rem */
  letter-spacing: -0.02rem;
}

/* Greeting (Scrollable) */
.greeting {
  padding: 0px 20px 30px;
  text-align: center;
  background: url('/images/bg_gra.png') center top/100% 40% no-repeat;
  margin: -16px -16px 16px -16px;
}

.logo {
  height: 172px;
  /* filter: drop-shadow(0 2px 8px rgba(0,0,0,0.1)); */
}

.greeting h3 {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.3px;
  line-height: 140%;
}

.greeting p {
  font-weight: 700;
  display: inline;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
  -webkit-overflow-scrolling: touch;
}

.chat-body::-webkit-scrollbar {
  display: none;
}

/* Action Buttons */

.action-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.action-buttons {
  display: flex;
  gap: 8px;
  padding: 12px 16px 8px;
  background: #fff;
  border-top: 1px solid #f0f0f0;
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid #e5e5ea;
  background: #fff;
  /* border-radius: 12px; */
  border-radius: var(--Radius-2XS, 75rem);
  color: var(--Colors-Black-100, #121212);
  /* Global Tokens/Pretendard/button 2 */
  font-family: Pretendard;
  font-size: 0.875rem;
  font-style: normal;
  font-weight: 600;
  line-height: 150%; /* 1.3125rem */
  letter-spacing: -0.0175rem;
  cursor: pointer;
}

.action-btn:active, .action-btn:hover {
  transform: scale(0.97);
  background: var(--Colors-White-200, #F4F4F4);
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}

.action-btn img {
  vertical-align: middle;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

.action-btn:disabled:active,
.action-btn:disabled:hover {
  transform: none !important;
  background: #fff !important;
}

.message {
  display: flex;
  margin-bottom: 16px;
  align-items: flex-start;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  justify-content: flex-end;
}

.message.bot {
  justify-content: flex-start;
}

.bubble-wrapper {
  display: flex;
  flex-direction: column;
  max-width: 80%;
}

.bubble {
  background: #fff;
  padding: 14px 16px;
  border-radius: 20px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04);
  font-size: 15px;
  line-height: 150%;
  letter-spacing: -0.2px;
}

.bubble p {
  margin: 0;
}

.bubble .hint {
  /* color: #8e8e93; */
  font-size: 16px;
}

.bubble .hint small {
  font-size: 13px;
}

.message-with-icon {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.message-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  margin-top: 2px;
}

.message-with-icon p {
  margin: 0;
  flex: 1;
}

.bubble.alert {
  background: transparent;
}

.bubble.error {
  background: #FFF3F3 !important;
  color: #FF3B30;
}

.message.user .bubble-wrapper {
  align-items: flex-end;
}

.message.user .bubble {
  width: 100%;
  word-break: break-word;
  background: #DBF8FA;
  color: #1c1c1e;
  /* padding: 12px 16px; */
  border-radius: 20px 4px 20px 20px;
}

.message.bot .bubble {
  background: #F4F4F4;
  border-radius: 4px 20px 20px 20px;
}

.message.bot.welcome .bubble {
  background: #fff;
}

.timestamp {
  font-size: 11px;
  color: #8e8e93;
  margin-top: 4px;
  padding: 0 8px;
  font-weight: 400;
}

.bubble.muted {
  background: #e5e5ea;
  color: #3c3c43;
}

.loading-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fff;
  border-radius: 4px 20px 20px 20px;
  font-size: 16px;
  line-height: 150%;
  letter-spacing: -0.32px;
}

.loading-bubble.error {
  background: #FFF3F3;
  color: #FF3B30;
}

.loading-bubble.alert {
  background: #fff;
}

.loading-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.regret-points {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.regret-btn {
  background: linear-gradient(135deg, #5E5CE6 0%, #007AFF 100%);
  color: white;
  border: none;
  border-radius: 14px;
  padding: 14px 18px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  text-align: left;
  letter-spacing: -0.2px;
  box-shadow: 0 2px 8px rgba(94, 92, 230, 0.3);
  -webkit-tap-highlight-color: transparent;
}

.regret-btn:active {
  transform: scale(0.97);
  box-shadow: 0 1px 4px rgba(94, 92, 230, 0.2);
}

.reviews-evidence {
  margin-bottom: 16px;
}

.evidence-title {
  font-size: 14px;
  font-weight: 600;
  color: #1c1c1e;
  margin-bottom: 12px;
  letter-spacing: -0.2px;
}

.review-summary {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: #1c1c1e;
  margin-top: 4px;
}

.review-item {
  background: white;
  padding: 12px;
  border-radius: 12px;
  margin-bottom: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.review-item:last-child {
  margin-bottom: 0;
}

.review-rating {
  font-size: 12px;
  color: #ff9500;
  margin-bottom: 6px;
  font-weight: 600;
}

.review-text {
  font-size: 14px;
  color: #3c3c43;
  line-height: 150%;
  letter-spacing: -0.2px;
}

.option-list {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.option-list button {
  border-radius: 1.25rem;
  border: 1px solid var(--Colors-Blue-200, #C2E0FF);
  background: var(--Colors-White-100, #FFF);
  padding: 8px 16px;
  color: var(--Colors-Bule-300, #017FFF);
  font-family: Pretendard;
  font-size: 1rem;
  font-style: normal;
  font-weight: 600;
  line-height: 150%; /* 1.5rem */
  letter-spacing: -0.02rem;
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}

.option-list button:active {
  transform: scale(0.95);
  border: 1px solid var(--Colors-Blue-200, #C2E0FF);
  background: var(--Colors-Blue-100, #E4F2FF);
}

/* 별점 선택 UI */
.rating-container {
  margin-top: 16px;
  padding: 12px;
  background: rgba(255, 193, 7, 0.05);
  border-radius: 12px;
  text-align: center;
}

.rating-stars {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 8px;
}

.rating-stars .star {
  font-size: 2rem;
  cursor: pointer;
  transition: all 0.2s;
  filter: grayscale(1);
  opacity: 0.3;
  -webkit-tap-highlight-color: transparent;
}

.rating-stars .star.filled {
  filter: grayscale(0);
  opacity: 1;
  transform: scale(1.2);
}

.rating-stars .star:hover {
  transform: scale(1.3);
}

.rating-stars .star:active {
  transform: scale(1.1);
}

.input-area {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  padding-bottom: max(env(safe-area-inset-bottom), 8px);
  /* border-top: 0.5px solid rgba(0,0,0,0.1); */
}

.input-wrapper {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  background: transparent;
}

.input-area input {
  flex: 1;
  border: none;
  background: #fff;
  padding: 10px 42px 10px 16px;
  font-size: 16px;
  outline: none;
  /* border: solid 2px #d1d1d6; */
  box-shadow: 0 0 4px 0 rgba(0, 0, 0, 0.20);
  border-radius: 1.375rem;
  letter-spacing: -0.2px;
  color: #1c1c1e;
}

.input-area input::placeholder {
  color: #999;
}

.input-area input:focus {
  background: #fff;
}

.input-area button {
  position: absolute;
  right: 8px;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
  -webkit-tap-highlight-color: transparent;
}

.input-area button img {
  width: 100%;
  height: 100%;
  display: block;
}

.input-area button:active {
  transform: scale(0.9);
}

.input-area button:disabled {
  opacity: 0.3;
}

/* Markdown 스타일 */
.bubble h1,
.bubble h2,
.bubble h3 {
  margin: 16px 0 8px;
  font-weight: 700;
  color: #1c1c1e;
  line-height: 1.3;
}

.bubble h1 {
  font-size: 20px;
}

.bubble h2 {
  font-size: 18px;
}

.bubble h3 {
  font-size: 16px;
}

.bubble strong {
  font-weight: 700;
  color: #007AFF;
}

.bubble em {
  font-style: italic;
  color: #5E5CE6;
}

.bubble ul,
.bubble ol {
  margin: 8px 0;
  padding-left: 24px;
}

.bubble li {
  margin: 4px 0;
  line-height: 1.5;
}

.bubble p {
  margin: 8px 0;
}

.bubble p:first-child {
  margin-top: 0;
}

.bubble p:last-child {
  margin-bottom: 0;
}

.bubble code {
  background: #f5f5f7;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  font-size: 14px;
  color: #FF3B30;
}

.bubble pre {
  background: #f5f5f7;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.bubble pre code {
  background: transparent;
  padding: 0;
  color: #1c1c1e;
}

.bubble blockquote {
  border-left: 3px solid #007AFF;
  padding-left: 12px;
  margin: 8px 0;
  color: #8e8e93;
}
</style>