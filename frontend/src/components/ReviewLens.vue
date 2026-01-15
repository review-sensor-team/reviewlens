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

      <!-- Welcome (메시지가 없을 때만 표시) -->
      <div v-if="messages.length === 0" class="message bot">
        <div class="bubble-wrapper">
          <div class="bubble">
            <p class="hint">
              제가 분석할 상품 URL을 입력해주세요.<br />
              <small>부정적인 리뷰만 분석합니다</small>
            </p>
          </div>
          <div class="timestamp">{{ formatTimestamp() }}</div>
        </div>
      </div>

      <!-- Messages -->
      <template v-for="(msg, idx) in messages" :key="idx">
        <div :class="['message', msg.role]">
          <div class="bubble-wrapper">
            <div class="bubble" :class="msg.messageType">
              <!-- 리뷰 근거 출력 -->
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

              <div v-if="msg.messageType" class="message-with-icon">
                <img :src="getMessageIcon(msg.messageType)" alt="아이콘" class="message-icon" />
                <div v-html="msg.text"></div>
              </div>
              <p v-else v-html="msg.text"></p>

              <!-- 후회 포인트 버튼 -->
              <div v-if="msg.regretPoints" class="option-list">
                <button
                  v-for="point in msg.regretPoints"
                  :key="point"
                  @click="selectRegretPoint(point)"
                >
                  {{ point }}
                </button>
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
      </template>

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
        <span><img src="/images/ic_rotate-cw.png" alt="삭제" class="action-icon" /> 링크 재분석</span>
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
import { ref, nextTick } from 'vue'
import { startSession, sendMessage, resetSession } from '../api/chat.js'
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

const pushBot = (text, options = null, regretPoints = null, reviews = null, messageType = null, reviewSummary = null) => {
  messages.value.push({ 
    role: 'bot', 
    text, 
    options, 
    regretPoints, 
    reviews,
    messageType,
    reviewSummary,
    timestamp: formatTimestamp()
  })
  scrollBottom()
}

const pushUser = (text) => {
  messages.value.push({ 
    role: 'user', 
    text,
    timestamp: formatTimestamp()
  })
  scrollBottom()
}

/** 최초 URL 입력 또는 추가 질문 */
const send = async () => {
  if (!input.value.trim()) return

  const text = input.value
  input.value = ''
  
  // URL 패턴 확인 (http:// 또는 https://로 시작하거나 일반적인 URL 형태)
  const isUrl = /^https?:\/\/.+/.test(text.trim()) || 
                /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/.test(text.trim())
  
  // URL이면 기존 세션 초기화
  if (isUrl && sessionId.value) {
    sessionId.value = null
  }
  
  pushUser(text)

  // 1. URL 입력 → 후회 포인트 도출
  if (!sessionId.value) {
    loading.value = true
    startLoadingTimer()
    loadingType.value = 'search'
    loadingText.value = '상품 리뷰를 수집 중이에요...'
    
    try {
      const res = await startSession(text)
      sessionId.value = res.session_id      
      console.log('세션 생성 완료:', res.session_id)
      console.log('suggested_factors:', res.suggested_factors)
      // 2. 시스템 상태 메시지 (분석 완료)
      loadingType.value = 'analyze'
      loadingText.value = '후회 포인트를 분석 중이에요...'
      await new Promise(r => setTimeout(r, 800))

      // 3. 후회 포인트 버튼 출력
      const productName = res.product_name || '이 상품'
      const reviewCount = res.total_count || 0
      pushBot(
        `<span style="color: #017FFF; font-weight: 400;">${productName}</span>의<br />별점 낮은 순으로 ${reviewCount}건에서 후회 포인트를 분석해 보았어요.<br />
아래 키워드를 선택하면 해당 리뷰 키워드와 관련된 리뷰를 보여드릴께요.<br />
혹은 궁금하신 점을 질문해 주시면 관련해서 자세히 설명 드릴께요.`,
        null,
        res.suggested_factors,
        null,
        'analyze'  // messageType을 'analyze'로 설정
      )
    } catch (e) {
      const error_prefix = '리뷰 수집 중';
      // 오류 처리
      if(loadingType.value === 'search') {
        loadingType.value = 'error'
        loadingText.value = '리뷰 수집에 실패했어요.'
      } else {
        loadingType.value = 'error'
        loadingText.value = '후회 포인트 분석에 실패했어요.'
        error_prefix = '후회 포인트 분석 중';
      }
      await new Promise(r => setTimeout(r, 1000))
      loading.value = false

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
      return
    } finally {
      loading.value = false
      stopLoadingTimer()
    }
    return
  }

  // 5. 추가 질문 입력
  loading.value = true
  startLoadingTimer()
  loadingType.value = 'brief'
  loadingText.value = '답변을 생성 중이에요...'
  
  try {
    const res = await sendMessage(sessionId.value, text)

    if (res.is_final) {
      // 최종 요약
      pushBot(res.bot_message)
    } else {
      // 일반 응답 + 옵션
      pushBot(res.bot_message, res.options)
    }
  } catch (e) {

    pushBot('<div class="message-with-icon"><img src="/images/error_icon.png" alt="아이콘" class="message-icon" /><div>죄송해요, 응답을 생성하는 중 오류가 발생했어요. 다시 시도해 주세요.</div></div>')
  } finally {
    loading.value = false
    stopLoadingTimer()
  }
}

/** 4. 후회 포인트 선택 시 리뷰 근거 출력 */
const selectRegretPoint = async (point) => {
  pushUser(point)
  
  console.log('후회 포인트 선택:', point)
  console.log('현재 세션 ID:', sessionId.value)
  
  loading.value = true
  startLoadingTimer()
  loadingType.value = 'search'
  loadingText.value = '관련 리뷰를 찾고 있어요...'
  
  try {
    // 후회 포인트를 selected_factor로 전달
    const res = await sendMessage(sessionId.value, point, point)
    
    console.log('sendMessage 응답:', res)
    
    // 리뷰 근거 출력 (related_reviews는 객체 형태)
    const hasReviews = res.related_reviews && Object.keys(res.related_reviews).length > 0
    
    if (hasReviews) {
      // related_reviews 객체를 배열로 변환하고 summary 생성
      const reviewsArray = []
      const termCounts = new Map()  // term별 중복 제거를 위해 Map 사용
      
      for (const factorKey in res.related_reviews) {
        const reviewInfo = res.related_reviews[factorKey]
        
        if (reviewInfo.examples && reviewInfo.examples.length > 0) {
          // term_counts 사용 (각 anchor_term별 리뷰 수)
          if (reviewInfo.term_counts) {
            for (const [term, count] of Object.entries(reviewInfo.term_counts)) {
              if (!termCounts.has(term)) {
                termCounts.set(term, count)
              }
            }
          }
          
          // sentences를 문자열로 변환하여 배열에 추가
          reviewInfo.examples.forEach(example => {
            const text = Array.isArray(example.sentences) 
              ? example.sentences.join(' ') 
              : example.sentences
            
            reviewsArray.push({
              text: text,
              rating: example.rating
            })
          })
        }
      }
      
      // summary 문구 생성 (중복 제거된 term들로)
      const reviewSummary = termCounts.size > 0 
        ? Array.from(termCounts.entries()).map(([term, count]) => `'${term}'에 대해 ${count}건`).join(', ') + '을 찾았어요.'
        : null
      
      console.log('변환된 리뷰 배열:', reviewsArray)
      console.log('리뷰 요약:', reviewSummary)
      
      pushBot(
        res.bot_message,
        res.options,
        null,
        reviewsArray,
        null,
        reviewSummary
      )
    } else {
      pushBot(res.bot_message, res.options)
    }
  } catch (e) {
    console.error('리뷰 분석 오류:', e)
    console.error('오류 상세:', e.response?.data)
    pushBot('<div class="message-with-icon"><img src="/images/ic_x-circle.png" alt="아이콘" class="message-icon" /><p>죄송해요, 리뷰 분석 중 오류가 발생했어요.</p>')
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
  loadingText.value = '답변을 생성 중이에요...'
  
  try {
    const res = await sendMessage(sessionId.value, opt)
    
    // 분석 결과가 준비되었으면 표시
    if (res.has_analysis && res.llm_context) {
      const summary = res.llm_context.llm_summary || '분석 결과를 생성했습니다.'
      const htmlContent = convertMarkdownToHtml(summary)
      pushBot(htmlContent, null, null, null, 'analyze')
      
      // 분석 결과 표시 후 추가 안내 메시지
      pushBot('다른 상품에 대한 리뷰를 분석해 드릴까요? 제가 분석할 상품 URL을 입력해주세요.')
    } else {
      // 분석 결과가 없을 때만 다음 질문이나 메시지 표시
      if (res.bot_message) {
        pushBot(res.bot_message, res.options)
      }
    }
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
    
    // 분석 결과 메시지(messageType === 'analyze')의 인덱스를 찾음
    let analyzeMessageIndex = -1
    for (let i = messages.value.length - 1; i >= 0; i--) {
      if (messages.value[i].messageType === 'analyze') {
        analyzeMessageIndex = i
        break
      }
    }
    
    if (analyzeMessageIndex !== -1) {
      // 분석 결과까지만 남기고 나머지 삭제
      messages.value = messages.value.slice(0, analyzeMessageIndex + 1)
    } else {
      // 분석 결과가 없으면 첫 번째 사용자 메시지(URL)까지만 남김
      const urlInputIndex = messages.value.findIndex(msg => msg.role === 'user')
      if (urlInputIndex !== -1) {
        messages.value = messages.value.slice(0, urlInputIndex + 1)
      }
    }
    
    scrollBottom()
  } catch (error) {
    console.error('세션 재분석 실패:', error)
    // 에러가 발생해도 UI는 초기화
    let analyzeMessageIndex = -1
    for (let i = messages.value.length - 1; i >= 0; i--) {
      if (messages.value[i].messageType === 'analyze') {
        analyzeMessageIndex = i
        break
      }
    }
    
    if (analyzeMessageIndex !== -1) {
      messages.value = messages.value.slice(0, analyzeMessageIndex + 1)
    } else {
      const urlInputIndex = messages.value.findIndex(msg => msg.role === 'user')
      if (urlInputIndex !== -1) {
        messages.value = messages.value.slice(0, urlInputIndex + 1)
      }
    }
    
    scrollBottom()
  }
}

/** 다른 상품 리뷰 분석 (세션 완전 초기화) */
const startNewAnalysis = () => {
  // 모든 메시지 삭제
  messages.value = []
  
  // 세션 초기화
  sessionId.value = null
  
  scrollBottom()
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
  border-top-left-radius: 20px;
  border-top-right-radius: 4px;
  border-bottom-right-radius: 20px;
  border-bottom-left-radius: 20px;
}

.message.bot .bubble {
  background: #F4F4F4;
  border-top-left-radius: 4px;
  border-top-right-radius: 20px;
  border-bottom-right-radius: 20px;
  border-bottom-left-radius: 20px;
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
  border-top-left-radius: 4px;
  border-top-right-radius: 20px;
  border-bottom-right-radius: 20px;
  border-bottom-left-radius: 20px;
  color: #017FFF;
  font-family: Pretendard, -apple-system, BlinkMacSystemFont, sans-serif;
  font-weight: 400;
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