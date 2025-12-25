개발자 가이드

환경 준비

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

테스트 실행

```bash
pytest -q
```

테스트는 `tests/test_demo_scenario.py`를 실행하여 3~5턴 대화 시나리오를 재현합니다.
