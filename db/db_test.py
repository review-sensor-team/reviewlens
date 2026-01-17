# # -------------------------------------------------
# # PostgreSQL setup test >> ('PostgreSQL 16.11, compiled by Visual C++ build 1944, 64-bit',)
# # -------------------------------------------------
# import psycopg2

# conn = psycopg2.connect(
#     host="localhost",
#     port=5432,
#     dbname="reviewlens",
#     user="postgres",
#     password="sqsq2601"
# )
# cur = conn.cursor()
# cur.execute("SELECT version();")
# print(cur.fetchone())
# cur.close()
# conn.close()



# -------------------------------------------------
# reg_store_test.py
# -------------------------------------------------
# import sys
# from pathlib import Path
# sys.path.append(str(Path(__file__).resolve().parents[1]))
        # (.venv) PS C:\reviewlens> python -m db.db_test  

from backend.pipeline.reg_store_db import RegStore

def main():
    store = RegStore(
        host="localhost",
        port=5432,
        dbname="reviewlens",
        user="postgres",
        password="sqsq2601",  # 실제 비밀번호
    )

    # 1. factors 로드
    factors = store.load_factors(product_no=1)
    print(f"[factors] count = {len(factors)}")
    print("sample factor:", factors[0])

    # 2. questions 로드
    questions = store.load_questions(product_no=1)
    print(f"[questions] count = {len(questions)}")
    print("sample question:", questions[0])

    # 3. 관계 검증
    factor_ids = {f.factor_id for f in factors}
    assert all(q.factor_id in factor_ids for q in questions)

    # 4. terms 파싱 검증
    assert isinstance(factors[0].anchor_terms, list)
    print("anchor_terms:", factors[0].anchor_terms)

    store.close()
    print("✅ reg_store DB test passed")

if __name__ == "__main__":
    main()
