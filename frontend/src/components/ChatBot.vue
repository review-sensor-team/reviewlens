<!-- ChatBot.vue -->
<template>
  <div class="chat-container">
    <div class="chat-header">
      <h1>💬 ReviewLens</h1>
      <p>후회를 줄이는 대화형 리뷰 분석</p>
    </div>

    <!-- 리뷰 수집 중 오버레이 -->
    <div v-if="isCollectingReviews" class="collecting-overlay">
      <div class="collecting-animation">
        <div class="spinner"></div>
        <h3>🔍 리뷰 수집 중...</h3>
        <p>별점 낮은 리뷰들을 꼼꼼히 모으고 있어요</p>
        <p class="collecting-subtext">최대 2분 정도 소요될 수 있습니다</p>
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <!-- 메시지 목록 -->
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['message', msg.role]"
      >
        <div class="message-content">
          <!-- 질문 번호 표시 (봇 메시지 && 질문 있을 때) -->
          <div v-if="msg.role === 'bot' && msg.questionId" class="question-number">
            💬 질문 {{ msg.questionId }}
          </div>

          <div class="message-text">{{ msg.text }}</div>

          <!-- 선택지 버튼 (single_choice 타입) -->
          <div
            v-if="msg.role === 'bot' && msg.choices && msg.choices.length > 0 && !msg.answered"
            class="choices"
          >
            <button
              v-for="(choice, idx) in msg.choices"
              :key="idx"
              @click="handleChoiceClick(choice, index)"
              class="choice-button"
              :disabled="isLoading || isCollectingReviews"
            >
              {{ choice }}
            </button>
          </div>

          <!-- 요인 뱃지 표시 (봇 메시지에만) -->
          <div
            v-if="msg.role === 'bot' && msg.factors && msg.factors.length > 0"
            class="factors"
          >
            <div class="factors-label">🎯 주요 후회 요인:</div>
            <div class="factor-badges">
              <span
                v-for="(factor, idx) in msg.factors"
                :key="idx"
                class="factor-badge"
              >
                {{ factor.display_name || factor.factor_key }}
                <small>({{ Number(factor.score ?? 0).toFixed(2) }})</small>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 로딩 표시 -->
      <div v-if="isLoading" class="message bot">
        <div class="message-content">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 최종 결과 표시 -->
    <div v-if="finalResult" class="final-result">
      <h3>📊 후회 요인 분석 결과</h3>

      <!-- 계산 공식 표시 -->
      <div v-if="finalResult.llm_context?.calculation_info" class="calculation-info">
        <h4>📊 후회 요인 계산 로직</h4>
        <div class="formula-box">
          <div class="formula-item">
            <strong>기본 점수 계산:</strong>
            <code>{{ finalResult.llm_context.calculation_info.scoring_formula }}</code>
          </div>
          <div class="formula-item">
            <strong>평점 가중치:</strong>
            <code>{{ finalResult.llm_context.calculation_info.rating_multiplier_formula }}</code>
          </div>
          <div class="formula-item">
            <strong>총 대화 턴:</strong>
            <span class="turn-count">{{ finalResult.llm_context.calculation_info.total_turns }}턴</span>
          </div>
        </div>

        <!-- 누적 점수 표시 -->
        <div class="cumulative-scores">
          <h5>📈 누적 점수 (전체 요인)</h5>
          <div class="score-grid">
            <div
              v-for="(score, factor) in finalResult.llm_context.calculation_info.cumulative_scores"
              :key="factor"
              class="score-item"
              :class="{ 'top-factor': isTopFactor(String(factor)) }"
            >
              <span class="factor-name">{{ factor }}</span>
              <span class="factor-score">{{ score }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="result-summary">
        <p><strong>주요 후회 요인:</strong></p>
        <div class="factor-list">
          <div
            v-for="(factor, idx) in normalizedTopFactors"
            :key="idx"
            class="factor-item"
          >
            {{ idx + 1 }}. {{ factor.display_name || factor.factor_key }}
            (점수: {{ Number(factor.score ?? 0).toFixed(2) }})
          </div>
        </div>

        <p class="evidence-count">
          📋 증거 리뷰: {{ finalResult.llm_context?.evidence_reviews?.length || 0 }}개
        </p>

        <!-- ✅ 증거 리뷰 미리보기 -->
        <div
          v-if="finalResult.llm_context?.evidence_reviews?.length"
          class="evidence-preview"
        >
          <h4>🧾 증거 리뷰 미리보기 (상위 10개)</h4>
          <ul class="evidence-list">
            <li
              v-for="e in finalResult.llm_context.evidence_reviews.slice(0, 10)"
              :key="e.review_id"
              class="evidence-item"
            >
              <strong>[{{ e.label || 'NEU' }}]</strong>
              <span class="evidence-meta">({{ e.rating }}점)</span>
              <span class="evidence-text">{{ e.excerpt }}</span>
            </li>
          </ul>
        </div>

        <button @click="resetChat" class="reset-button">
          새로운 분석 시작
        </button>
      </div>
    </div>

    <!-- 입력 영역 -->
    <div v-if="!finalResult" class="chat-input">
      <input
        v-model="userInput"
        @keyup.enter="handleUserInput"
        :disabled="isLoading || isCollectingReviews"
        :placeholder="getInputPlaceholder()"
        class="input-field"
      />
      <button
        @click="handleUserInput"
        :disabled="isLoading || !userInput.trim() || isCollectingReviews"
        class="send-button"
      >
        전송
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { startChatSession, sendMessage, collectReviews } from '../api'
import axios from 'axios'

// 상태 관리
const sessionId = ref(null)
const messages = ref([])
const userInput = ref('')
const isLoading = ref(false)
const finalResult = ref(null)
const messagesContainer = ref(null)

// 리뷰 수집 관련 상태
const isCollectingReviews = ref(false)
const reviewsCollected = ref(false)
const collectedReviewCount = ref(0)
const waitingForUrl = ref(true) // URL 대기 상태

// 현재 카테고리 (리뷰 수집 시 감지)
const currentCategory = ref('appliance_heated_humidifier')

/**
 * ✅ 백엔드 응답이 object 형태([{factor_key, score}])든
 * tuple 형태([["noise_sleep", 3.12], ...])든 안전하게 처리
 */
const normalizedTopFactors = computed(() => {
  const arr = finalResult.value?.top_factors || []
  return arr.map((f) => {
    if (Array.isArray(f)) {
      return { factor_key: f[0], score: Number(f[1] ?? 0), display_name: f[0] }
    }
    return {
      factor_key: f.factor_key,
      score: Number(f.score ?? 0),
      display_name: f.display_name || f.factor_key
    }
  })
})

// URL 패턴 감지
const isValidUrl = (text) => {
  const urlPattern = /(https?:\/\/[^\s]+)/g
  return urlPattern.test(text)
}

// 사용자 입력 처리
const handleUserInput = async () => {
  if (!userInput.value.trim() || isLoading.value || isCollectingReviews.value) return

  const message = userInput.value.trim()

  // URL 대기 중인 경우
  if (waitingForUrl.value) {
    if (isValidUrl(message)) {
      await collectProductReviews(message)
    } else {
      // URL이 아닌 경우 재안내
      messages.value.push({
        role: 'user',
        text: message
      })
      messages.value.push({
        role: 'bot',
        text: '음... 그건 상품 링크가 아닌 것 같아요 🤔\n\n네이버 스마트스토어 상품 링크를 붙여넣어 주세요!\n(예: https://brand.naver.com/airmade/products/...)'
      })
      scrollToBottom()
    }
    userInput.value = ''
    return
  }

  // 일반 채팅
  await sendUserMessage()
}

// 리뷰 수집
const collectProductReviews = async (productUrl) => {
  // 사용자 메시지 추가
  messages.value.push({
    role: 'user',
    text: productUrl
  })

  scrollToBottom()

  try {
    isCollectingReviews.value = true

    const response = await collectReviews(productUrl, 100, true)

    if (response.success && response.reviews && response.reviews.length > 0) {
      collectedReviewCount.value = response.total_count
      reviewsCollected.value = true
      waitingForUrl.value = false

      // 수집 완료 메시지
      messages.value.push({
        role: 'bot',
        text: `굿! 👍 리뷰 ${response.total_count}건을 모았어요.\n별점 낮은 리뷰들을 우선적으로 가져왔습니다.\n\n이제 궁금한 점을 물어보세요!`
      })

      scrollToBottom()

      // 세션 시작하고 리뷰 데이터 저장
      await initSessionWithReviews(response.reviews)
    } else {
      messages.value.push({
        role: 'bot',
        text: '앗, 리뷰를 가져오는데 실패했어요 😢\n\n다른 상품 링크로 다시 시도해주세요!'
      })
      scrollToBottom()
    }
  } catch (error) {
    console.error('리뷰 수집 오류:', error)
    const errorMsg = error.response?.data?.detail || error.message
    messages.value.push({
      role: 'bot',
      text: `리뷰 수집 중 문제가 생겼어요 😅\n\n오류: ${errorMsg}\n\n다시 시도해볼까요?`
    })
    scrollToBottom()
  } finally {
    isCollectingReviews.value = false
  }
}

// 입력 플레이스홀더
const getInputPlaceholder = () => {
  if (isCollectingReviews.value) return '리뷰 수집 중...'
  if (waitingForUrl.value) return '스마트스토어 상품 링크를 붙여넣어 주세요 🔗'
  if (isLoading.value) return '생각 중...'
  return '궁금한 점을 입력하세요...'
}

// 초기 환영 메시지
const showWelcomeMessage = () => {
  messages.value.push({
    role: 'bot',
    text: '안녕하세요! 👋\n\n저는 ReviewLens 봇이에요.\n후회하지 않는 쇼핑을 도와드릴게요!\n\n먼저, 분석하고 싶은 **네이버 스마트스토어 상품 링크**를 붙여넣어 주세요.\n별점 낮은 리뷰들을 모아서 후회 요인을 분석해드릴게요! 🔍'
  })
  scrollToBottom()
}

// 세션 시작
const initSession = async () => {
  try {
    isLoading.value = true

    // ✅ 데모 타겟 카테고리로 변경
    const response = await startChatSession('appliance_heated_humidifier')
    sessionId.value = response.session_id

    // 세션 시작 메시지는 표시하지 않음 (이미 수집 완료 메시지 표시됨)
  } catch (error) {
    console.error('세션 시작 오류:', error)
    messages.value.push({
      role: 'bot',
      text: '⚠️ 서버 연결에 실패했습니다. 백엔드 서버가 실행 중인지 확인해주세요.'
    })
  } finally {
    isLoading.value = false
  }
}

// 리뷰 데이터와 함께 세션 시작
const initSessionWithReviews = async (reviews) => {
  try {
    isLoading.value = true

    // 세션 먼저 생성
    const response = await startChatSession('appliance_heated_humidifier')
    sessionId.value = response.session_id

    // 리뷰 데이터를 세션에 저장
    await axios.post('/api/chat/start-with-reviews', {
      session_id: sessionId.value,
      reviews: reviews
    })
  } catch (error) {
    console.error('세션 시작 오류:', error)
    messages.value.push({
      role: 'bot',
      text: '⚠️ 서버 연결에 실패했습니다. 백엔드 서버가 실행 중인지 확인해주세요.'
    })
  } finally {
    isLoading.value = false
  }
}

// 선택지 버튼 클릭 처리
const handleChoiceClick = async (choice, messageIndex) => {
  // 해당 메시지를 answered 처리하여 버튼 비활성화
  messages.value[messageIndex].answered = true
  
  // 선택한 답변을 사용자 메시지로 추가
  messages.value.push({
    role: 'user',
    text: choice
  })
  
  scrollToBottom()
  
  // 백엔드로 전송
  await sendMessageToBackend(choice)
}

// 사용자 메시지 전송
const sendUserMessage = async () => {
  if (!userInput.value.trim() || isLoading.value || !sessionId.value) return

  const message = userInput.value.trim()
  userInput.value = ''

  // 사용자 메시지 추가
  messages.value.push({
    role: 'user',
    text: message
  })

  scrollToBottom()
  
  await sendMessageToBackend(message)
}

// 백엔드로 메시지 전송 (공통 로직)
const sendMessageToBackend = async (message) => {
  try {
    isLoading.value = true
    const response = await sendMessage(sessionId.value, message)

    // 봇 응답 추가
    if (response.is_final) {
      // 최종 결과
      messages.value.push({
        role: 'bot',
        text: '대화를 분석하여 후회 요인을 파악했습니다. 아래에서 분석 결과를 확인해주세요.',
        factors: response.top_factors
      })
      finalResult.value = response
    } else {
      // 중간 질문
      const botMessage = {
        role: 'bot',
        text: response.bot_message || response.question_text || '다음 질문을 선택해주세요.',
        factors: response.top_factors,
        questionId: response.question_id || null,
        answerType: response.answer_type || 'no_choice',
        choices: [],
        answered: false
      }
      
      // single_choice인 경우 선택지 파싱
      if (response.answer_type === 'single_choice' && response.choices) {
        botMessage.choices = response.choices.split('|').map(c => c.trim())
      }
      
      messages.value.push(botMessage)
    }

    scrollToBottom()
  } catch (error) {
    console.error('메시지 전송 오류:', error)
    messages.value.push({
      role: 'bot',
      text: '⚠️ 메시지 전송에 실패했습니다.'
    })
  } finally {
    isLoading.value = false
  }
}

// 채팅 리셋
const resetChat = () => {
  messages.value = []
  finalResult.value = null
  sessionId.value = null
  userInput.value = ''
  reviewsCollected.value = false
  collectedReviewCount.value = 0
  isCollectingReviews.value = false
  waitingForUrl.value = true
  
  // 환영 메시지 다시 표시
  showWelcomeMessage()
}

// 스크롤 하단으로 이동
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// Top factor 여부 확인
const isTopFactor = (factorKey) => {
  return normalizedTopFactors.value.some((f) => f.factor_key === factorKey)
}

// 컴포넌트 마운트 시 환영 메시지 표시
onMounted(() => {
  showWelcomeMessage()
})
</script>

<style scoped>
.chat-container {
  max-width: 800px;
  margin: 0 auto;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.chat-header {
  padding: 1.5rem;
  background: #667eea;
  color: white;
  text-align: center;
  border-bottom: 2px solid #5568d3;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.collecting-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px)
}
.collecting-reviews {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  padding: 2rem;
}

.collecting-animation {
  text-align: center;
}

.spinner {
  width: 60px;
  height: 60px;
  margin: 0 auto 1.5rem;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.collecting-animation h3 {
  margin: 0 0 0.5rem 0;
  color: #333;
  font-size: 1.5rem;
}

.collecting-animation p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

/* 리뷰 수집 완료 정보 */
.review-collected-info {
  background: #d4edda;
  border-bottom: 2px solid #28a745;
  padding: 1rem;
  text-align: center;
}

.info-message {
  margin: 0;
  color: #155724;
  font-weight: 600;
  font-size: 0.95rem;
}

.chat-header h1 {
  margin: 0;
  font-size: 1.8rem;
}

.chat-header p {
  margin: 0.5rem 0 0 0;
  opacity: 0.9;
  font-size: 0.9rem;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  background: white;
}

.message {
  margin-bottom: 1rem;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.bot {
  justify-content: flex-start;
}

.message-content {
  max-width: 70%;
  padding: 0.75rem 1rem;
  border-radius: 1rem;
  word-wrap: break-word;
}

.message.user .message-content {
  background: #667eea;
  color: white;
  border-bottom-right-radius: 0.25rem;
}

.message.bot .message-content {
  background: #e9ecef;
  color: #333;
  border-bottom-left-radius: 0.25rem;
}

.message-text {
  margin-bottom: 0.5rem;
}

.factors {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(0,0,0,0.1);
}

.factors-label {
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #555;
}

.collecting-animation p {
  margin: 0.5rem 0;
  color: #666;
  font-size: 1rem;
  line-height: 1.5;
}

.collecting-subtext {
  font-size: 0.85rem !important;
  color: #999 !important;
  margin-top: 0.75rem !important
}

.factor-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.factor-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: #667eea;
  color: white;
  border-radius: 1rem;
  font-size: 0.8rem;
  font-weight: 500;
}

.factor-badge small {
  opacity: 0.8;
  margin-left: 0.25rem;
}

/* 질문 번호 */
.question-number {
  font-size: 0.75rem;
  color: #667eea;
  font-weight: 600;
  margin-bottom: 0.5rem;
  padding: 0.25rem 0.5rem;
  background: rgba(102, 126, 234, 0.1);
  border-radius: 0.5rem;
  display: inline-block;
}

/* 선택지 버튼 */
.choices {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.choice-button {
  width: 100%;
  padding: 0.75rem 1rem;
  background: white;
  color: #667eea;
  border: 2px solid #667eea;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.choice-button:hover:not(:disabled) {
  background: #667eea;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
}

.choice-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.typing-indicator {
  display: flex;
  gap: 0.25rem;
  padding: 0.5rem 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #999;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  30% {
    opacity: 1;
    transform: translateY(-10px);
  }
}

.final-result {
  background: #fff;
  border-top: 2px solid #667eea;
  padding: 1.5rem;
  margin: 0;
  max-height: 50vh;
  overflow-y: auto;
  flex: 0 0 auto;
}

.final-result h3 {
  margin-top: 0;
  color: #667eea;
}

.calculation-info {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 0.5rem;
  margin: 1rem 0;
}

.calculation-info h4 {
  margin-top: 0;
  color: #333;
  font-size: 1.1rem;
}

.calculation-info h5 {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  color: #555;
  font-size: 1rem;
}

.formula-box {
  background: white;
  padding: 1rem;
  border-radius: 0.5rem;
  border-left: 4px solid #667eea;
  margin: 1rem 0;
}

.formula-item {
  margin: 0.75rem 0;
  line-height: 1.6;
}

.formula-item strong {
  display: block;
  margin-bottom: 0.25rem;
  color: #555;
  font-size: 0.9rem;
}

.formula-item code {
  background: #e9ecef;
  padding: 0.25rem 0.75rem;
  border-radius: 0.25rem;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.9rem;
  color: #d63384;
  display: inline-block;
}

.turn-count {
  background: #667eea;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 0.25rem;
  font-weight: 600;
}

.cumulative-scores {
  margin-top: 1rem;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.score-item {
  background: white;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 2px solid #e9ecef;
  transition: all 0.2s;
}

.score-item.top-factor {
  border-color: #667eea;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
}

.factor-name {
  font-weight: 600;
  color: #333;
  font-size: 0.9rem;
}

.factor-score {
  font-weight: 700;
  color: #667eea;
  font-size: 1.1rem;
}

.score-item.top-factor .factor-score {
  color: #5568d3;
}

.result-summary {
  margin-top: 1rem;
}

.factor-list {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 0.5rem;
  margin: 1rem 0;
}

.factor-item {
  padding: 0.5rem 0;
  border-bottom: 1px solid #dee2e6;
}

.factor-item:last-child {
  border-bottom: none;
}

.evidence-count {
  color: #666;
  font-size: 0.95rem;
  margin: 1rem 0;
}

/* ✅ 증거 리뷰 미리보기 */
.evidence-preview {
  margin-top: 1rem;
  background: #f8f9fa;
  border-radius: 0.5rem;
  padding: 1rem;
}

.evidence-preview h4 {
  margin: 0 0 0.75rem 0;
  color: #333;
  font-size: 1rem;
}

.evidence-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 0.5rem;
}

.evidence-item {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 0.5rem;
  padding: 0.75rem;
  font-size: 0.9rem;
  line-height: 1.4;
}

.evidence-meta {
  margin-left: 0.5rem;
  color: #666;
  font-size: 0.85rem;
}

.evidence-text {
  display: block;
  margin-top: 0.35rem;
  color: #333;
}

.reset-button {
  width: 100%;
  padding: 0.75rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.reset-button:hover {
  background: #5568d3;
}

.chat-input {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  background: white;
  border-top: 1px solid #dee2e6;
}

.input-field {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #e9ecef;
  border-radius: 2rem;
  font-size: 1rem;
  outline: none;
  transition: border-color 0.2s;
}

.input-field:focus {
  border-color: #667eea;
}

.input-field:disabled {
  background: #f8f9fa;
  cursor: not-allowed;
}

.send-button {
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 2rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.send-button:hover:not(:disabled) {
  background: #5568d3;
}

.send-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

/* 모바일 반응형 스타일 */
@media (max-width: 768px) {
  .chat-container {
    max-width: 100%;
    height: 100vh;
  }

  .chat-header {
    padding: 1rem;
  }

  .chat-header h1 {
    font-size: 1.4rem;
  }

  .chat-header p {
    font-size: 0.8rem;
  }

  .chat-messages {
    padding: 0.75rem;
  }

  .message-content {
    max-width: 85%;
    font-size: 0.9rem;
  }

  .factor-badge {
    font-size: 0.75rem;
    padding: 0.2rem 0.6rem;
  }

  .final-result {
    padding: 1rem;
    max-height: 60vh;
  }

  .final-result h3 {
    font-size: 1.2rem;
  }

  .calculation-info {
    padding: 1rem;
  }

  .calculation-info h4 {
    font-size: 1rem;
  }

  .formula-item {
    font-size: 0.85rem;
  }

  .score-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .chat-input {
    padding: 0.75rem;
    gap: 0.5rem;
  }

  .input-field {
    padding: 0.6rem 1rem;
    font-size: 0.9rem;
  }

  .send-button {
    padding: 0.6rem 1.2rem;
    font-size: 0.9rem;
    min-width: 60px;
  }

  .reset-button {
    padding: 0.6rem 1.2rem;
    font-size: 0.9rem;
  }
}

@media (max-width: 480px) {
  .chat-header h1 {
    font-size: 1.2rem;
  }

  .chat-header p {
    font-size: 0.75rem;
  }

  .message-content {
    max-width: 90%;
    font-size: 0.85rem;
    padding: 0.6rem 0.8rem;
  }

  .factor-badge {
    font-size: 0.7rem;
    padding: 0.15rem 0.5rem;
  }

  .final-result {
    padding: 0.75rem;
  }

  .final-result h3 {
    font-size: 1.1rem;
  }

  .calculation-info {
    padding: 0.75rem;
  }

  .formula-item {
    font-size: 0.8rem;
  }

  .score-grid {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .input-field {
    padding: 0.5rem 0.8rem;
    font-size: 0.85rem;
  }

  .send-button {
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
  }
}
</style>