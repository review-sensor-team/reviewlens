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
                상품 목록에서 선택하기
              </button>
              <button @click="showUrlInput">
                URL 직접 입력하기
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
            <!-- 분석 결과 (JSON 데이터로 렌더링) -->
            <div v-if="msg.analysisData" class="analysis-result">
              <h1 class="analysis-title">{{ msg.analysisData.productName || '제품' }} 분석 결과<span v-if="msg.analysisData.strategyName"> ({{ msg.analysisData.strategyName }})</span></h1>
              
              <div v-if="msg.analysisData.summary" class="analysis-section">
                <h2>요약</h2>
                <p>{{ msg.analysisData.summary }}</p>
              </div>
              
              <div v-if="msg.analysisData.key_findings && msg.analysisData.key_findings.length > 0" class="analysis-section">
                <h2>주요 발견사항</h2>
                <div v-for="(finding, idx) in msg.analysisData.key_findings" :key="idx" class="finding-item">
                  <h3>{{ idx + 1 }}. {{ finding.factor }} <span class="risk-badge" :class="'risk-' + finding.risk_level">{{ getRiskLabel(finding.risk_level) }}</span></h3>
                  <p>{{ finding.what_users_say }}</p>
                </div>
              </div>
              
              <div v-if="msg.analysisData.balanced_view" class="analysis-section">
                <h2>균형잡힌 시각</h2>
                
                <div v-if="msg.analysisData.balanced_view.pros && msg.analysisData.balanced_view.pros.length > 0">
                  <h3>장점</h3>
                  <ul>
                    <li v-for="(pro, idx) in msg.analysisData.balanced_view.pros" :key="idx">{{ pro.point }}</li>
                  </ul>
                </div>
                
                <div v-if="msg.analysisData.balanced_view.cons && msg.analysisData.balanced_view.cons.length > 0">
                  <h3>단점/주의사항</h3>
                  <ul>
                    <li v-for="(con, idx) in msg.analysisData.balanced_view.cons" :key="idx">{{ con.point }}</li>
                  </ul>
                </div>
                
                <div v-if="msg.analysisData.balanced_view.mixed && msg.analysisData.balanced_view.mixed.length > 0">
                  <h3>상황에 따라 다름</h3>
                  <ul>
                    <li v-for="(mix, idx) in msg.analysisData.balanced_view.mixed" :key="idx">{{ mix.point }}</li>
                  </ul>
                </div>
              </div>
              
              <div v-if="msg.analysisData.decision_rule" class="analysis-section">
                <h2>구매 결정 가이드</h2>
                
                <div v-if="msg.analysisData.decision_rule.if_buy && msg.analysisData.decision_rule.if_buy.length > 0">
                  <h3>구매를 고려해도 좋은 경우</h3>
                  <ul>
                    <li v-for="(condition, idx) in msg.analysisData.decision_rule.if_buy" :key="idx">{{ condition }}</li>
                  </ul>
                </div>
                
                <div v-if="msg.analysisData.decision_rule.if_hold && msg.analysisData.decision_rule.if_hold.length > 0">
                  <h3>보류가 나은 경우</h3>
                  <ul>
                    <li v-for="(condition, idx) in msg.analysisData.decision_rule.if_hold" :key="idx">{{ condition }}</li>
                  </ul>
                </div>
              </div>
              
              <div v-if="msg.analysisData.final_recommendation" class="analysis-section">
                <h2>최종 추천: {{ msg.analysisData.final_recommendation }}</h2>
              </div>
              
              <div v-if="msg.analysisData.one_line_tip" class="tip-section">
                <p><strong>Tip:</strong> {{ msg.analysisData.one_line_tip }}</p>
              </div>
            </div>
            
            <!-- 메시지 텍스트 먼저 표시 -->
            <div v-else-if="msg.messageType" class="message-with-icon">
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
                <img
                  v-for="star in 5"
                  :key="star"
                  :src="star <= (msg.hoverRating || 0) ? '/images/ic_star_filled.svg' : '/images/ic_star_empty.svg'"
                  alt="별"
                  class="star"
                  @mouseenter="msg.hoverRating = star"
                  @mouseleave="msg.hoverRating = 0"
                  @click="submitRating(star, msg.responseFile, msg.strategy)"
                />
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
import { useReviewLens } from '../composables/useReviewLens.js'
import './ReviewLens.css'

const {
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
} = useReviewLens()
</script>