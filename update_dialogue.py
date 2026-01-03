#!/usr/bin/env python3
"""dialogue.py의 _pick_next_question 메서드를 질문 정보 반환 버전으로 업데이트"""

# dialogue.py 수정
with open('backend/pipeline/dialogue.py', 'r', encoding='utf-8') as f:
    content = f.read()

# _pick_next_question 메서드 교체
old_method = '''    def _pick_next_question(self, top_factors: List[Tuple[str, float]]) -> str:
        # 질문 테이블이 없으면 기본 질문
        if self.questions_df is None or self.questions_df.empty or not self.q_key_col or not self.q_text_col:
            return self._fallback_question()

        # "집중 수렴" 전략:
        # - turn 1~2: top2까지 후보
        # - turn 3부터: top1에 더 집중
        focus = 2 if self.turn_count <= 2 else 1
        focus_factors = [k for k, _ in top_factors[:focus]]

        candidates: List[Tuple[int, str]] = []
        for factor_key in focus_factors:
            matches = self.questions_df[self.questions_df[self.q_key_col] == factor_key]

            # 부분일치(예: noise_sleep vs noise)
            if len(matches) == 0:
                prefix = factor_key.split("_")[0]
                matches = self.questions_df[self.questions_df[self.q_key_col].astype(str).str.contains(prefix, na=False)]

            if len(matches) == 0:
                continue

            for rec in matches.to_dict(orient="records"):
                q_text = str(rec.get(self.q_text_col) or "").strip()
                if not q_text:
                    continue
                if q_text in self.asked_questions:
                    continue

                prio = 999
                if self.q_prio_col:
                    try:
                        prio = int(rec.get(self.q_prio_col) or 999)
                    except Exception:
                        prio = 999

                candidates.append((prio, q_text))

        # 우선순위 낮은 숫자 먼저
        candidates.sort(key=lambda x: x[0])

        if candidates:
            picked = candidates[0][1]
            self.asked_questions.add(picked)
            return picked

        return self._fallback_question()'''

new_method = '''    def _pick_next_question(self, top_factors: List[Tuple[str, float]]) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        """다음 질문 선택 (question_text, question_id, answer_type, choices 반환)"""
        # 질문 테이블이 없으면 기본 질문
        if self.questions_df is None or self.questions_df.empty or not self.q_key_col or not self.q_text_col:
            return (self._fallback_question(), None, 'no_choice', None)

        # "집중 수렴" 전략:
        # - turn 1~2: top2까지 후보
        # - turn 3부터: top1에 더 집중
        focus = 2 if self.turn_count <= 2 else 1
        focus_factors = [k for k, _ in top_factors[:focus]]

        candidates: List[Tuple[int, str, str, str, str]] = []  # (priority, question_text, question_id, answer_type, choices)
        for factor_key in focus_factors:
            matches = self.questions_df[self.questions_df[self.q_key_col] == factor_key]

            # 부분일치(예: noise_sleep vs noise)
            if len(matches) == 0:
                prefix = factor_key.split("_")[0]
                matches = self.questions_df[self.questions_df[self.q_key_col].astype(str).str.contains(prefix, na=False)]

            if len(matches) == 0:
                continue

            for rec in matches.to_dict(orient="records"):
                q_text = str(rec.get(self.q_text_col) or "").strip()
                if not q_text:
                    continue
                if q_text in self.asked_questions:
                    continue

                prio = 999
                if self.q_prio_col:
                    try:
                        prio = int(rec.get(self.q_prio_col) or 999)
                    except Exception:
                        prio = 999
                
                # 질문 메타 정보 추출
                q_id = str(rec.get('question_id') or '')
                a_type = str(rec.get('answer_type') or 'no_choice')
                choices = str(rec.get('choices') or '') if a_type == 'single_choice' else ''

                candidates.append((prio, q_text, q_id, a_type, choices))

        # 우선순위 낮은 숫자 먼저
        candidates.sort(key=lambda x: x[0])

        if candidates:
            picked = candidates[0]
            self.asked_questions.add(picked[1])
            return (picked[1], picked[2], picked[3], picked[4])  # (question_text, question_id, answer_type, choices)

        return (self._fallback_question(), None, 'no_choice', None)'''

if old_method in content:
    content = content.replace(old_method, new_method)
    with open('backend/pipeline/dialogue.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ dialogue.py 수정 완료 - _pick_next_question 메서드 업데이트됨")
    print("   - 반환 타입: Tuple[str, Optional[str], Optional[str], Optional[str]]")
    print("   - 반환 값: (question_text, question_id, answer_type, choices)")
else:
    print("❌ old_method를 찾을 수 없습니다")
    print("   이미 수정되었거나 코드가 변경되었을 수 있습니다")
