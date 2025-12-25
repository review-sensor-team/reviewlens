## DEMO: 5-턴 시나리오 (소음 중심 수렴 예)

목표: 3~5 턴 이내에 사용자의 우려사항이 `noise_sleep` 요인으로 수렴하는 대화 플로우를 테스트한다.

환경: `backend/data`의 샘플 CSV들을 사용한다 (reg_factor.csv, reg_question.csv, review_sample.csv).

시나리오 요약 (예시 대화):
	•	Turn 1 (User): “가열식 가습기 밤에 틀어도 괜찮을까요? 소음이 걱정돼요.”
	•	Bot 질문(예상): “주로 밤이나 수면 중에 사용하실 예정인가요?”
	•	top1 예상: noise_sleep
	•	Turn 2 (User): “네, 아이 방에서 밤에 켜둘 것 같아요.”
	•	Bot 질문(예상): “소음이나 불빛에 민감한 편이신가요?”
	•	top1 예상: noise_sleep (안정화)
	•	Turn 3 (User): “빛도 싫고, 기계 소리에도 예민해요.”
	•	Bot 질문(예상): “가습기를 켜자마자 바로 효과가 나와야 하나요?” 또는 “청소/물 보충 번거로움은 괜찮으신가요?”
	•	top_factors 상위 2개: noise_sleep + (heating_time or maintenance)
	•	Turn 4 (User): “조금 기다려도 되는데, 청소는 귀찮아요.”
	•	Bot 질문(예상): “아이 또는 부모님이 사용할 예정인가요?”(이미 언급했으면 건너뛰어도 됨) 또는 “차가운 미스트보다 따뜻한 수증기를 선호하시나요?”
	•	top_factors: noise_sleep + maintenance
	•	Turn 5 (User): “아이랑 같이 쓰고, 따뜻한 수증기가 좋아요.”
	•	Finalize: LLM context 생성
	•	evidence는 top factors 기준으로 리뷰를 뽑고 POS/NEG/MIX로 버킷 정보를 포함

주의: 질문 선택 로직은 reg_question.csv를 기반으로 하되, 사용자가 이미 답한 내용(예: 아이 방)과 중복되는 질문은 스킵하는 간단한 중복 방지 규칙을 넣어라.