<!-- ChatBot.vue -->
<template>
  <div class="chat-container">
    <div class="chat-header">
      <h1>💬 ReviewLens</h1>
      <p>후회를 줄이는 대화형 리뷰 분석</p>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <!-- 메시지 목록 -->
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['message', msg.role]"
      >
        <div class="message-content">
          <div class="message-text">{{ msg.text }}</div>

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
        @keyup.enter="sendUserMessage"
        :disabled="isLoading || !sessionId"
        placeholder="궁금한 점을 입력하세요..."
        class="input-field"
      />
      <button
        @click="sendUserMessage"
        :disabled="isLoading || !userInput.trim() || !sessionId"
        class="send-button"
      >
        전송
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { startChatSession, sendMessage } from '../api'

// 상태 관리
const sessionId = ref(null)
const messages = ref([])
const userInput = ref('')
const isLoading = ref(false)
const finalResult = ref(null)
const messagesContainer = ref(null)

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

// 세션 시작
const initSession = async () => {
  try {
    isLoading.value = true

    // ✅ 데모 타겟 카테고리로 변경
    const response = await startChatSession('appliance_heated_humidifier')
    sessionId.value = response.session_id

    // 초기 메시지 추가
    messages.value.push({
      role: 'bot',
      text: response.message || '안녕하세요! 무엇이 궁금하신가요?'
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
      messages.value.push({
        role: 'bot',
        text: response.bot_message || response.question_text || '다음 질문을 선택해주세요.',
        factors: response.top_factors
      })
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
  initSession()
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

// 컴포넌트 마운트 시 세션 시작
onMounted(() => {
  initSession()
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1.5rem;
  text-align: center;
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