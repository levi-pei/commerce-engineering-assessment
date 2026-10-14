# Variant PDP Backend

From `app/backend`:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn store.api:app --reload --port 8000
pytest -q
```

SQLite is intentionally used to demonstrate persistence, idempotency, and transactional stock updates without external infrastructure. `BEGIN IMMEDIATE` serialises writers, and the conditional `UPDATE ... WHERE stock >= quantity` is the final oversell guard. A production database can use the same conditional update or a row lock inside a short transaction.
