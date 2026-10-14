# Commerce Engineering Assessment

This repository contains the requested A/B/C exercises and a small production-minded variant product-detail page. It prioritises deterministic state changes, safe retries, explicit failure behaviour, and concise, reviewable code.

## Repository structure

```text
A/                 Inventory reservation ledger and tests
B/                 Fulfilment split optimiser and tests
C/                 Xero integration review
app/backend/        FastAPI + SQLite API and tests
app/frontend/       React + TypeScript PDP and tests
PLAN.md             Implementation plan and acceptance checklist
```

## Prerequisites

- Python 3.12 (Python 3.11+ is supported by the application code)
- Node.js 20+

## Quick start

Install backend dependencies and start the API:

```bash
cd app/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn store.api:app --reload --port 8000
```

In a second terminal, install and start the frontend:

```bash
cd app/frontend
npm install
npm run dev
```

Open the URL printed by Vite. The development server proxies `/api` to `http://127.0.0.1:8000`.

## Test commands

Run from the repository root:

```bash
python3 -m unittest discover -s A/tests -v
python3 -m unittest discover -s B/tests -v

cd app/backend
pytest -q

cd ../frontend
npm test
npm run build
```

Verified during delivery:

- Task A: 6 unit tests passed.
- Task B: 7 unit tests passed, including 100 randomized cases checked against exhaustive search and a `W=30`, `Q=2000` case.
- Backend: 6 API tests passed, including idempotency and concurrent final-unit reservation.
- Frontend: 4 tests passed, including variant resolution, unavailable/impossible states, duplicate-click prevention, and quantity correction.
- Frontend production build passed. The live page was manually checked at desktop and 375px widths; product loading, option selection, disabled combinations, stock state, cart count, and success feedback were exercised against the FastAPI service.

## Task A notes

`A/main.py` reads standard input and prints one result for each command plus sorted open reservations. `InventoryLedger` validates a complete command before mutation. A syntactically valid event is processed even when its business rule fails; a malformed command is rejected but not recorded, because it cannot be trusted as an idempotency identity.

Per-command processing and duplicate detection are O(1) average time. Final ordering is O(R log R), where R is the open reservation count.

## Task B notes

The optimiser sorts warehouse IDs first, then uses a quantity/warehouse-count dynamic programme. It chooses the final solution by the exact required order:

1. Fewest warehouses.
2. Lowest shipping cost.
3. Lexicographically smallest sorted `(warehouse_id, allocated_quantity)` list.

For a warehouse allocation transition, a monotonic deque finds the best earlier quantity in its allowed stock window. This avoids enumerating all subsets or all split quantities. Complexity is O(W²Q) time and O(WQ) space.

## Task C notes

`C/README.md` documents tenant verification, 401/403/404 diagnosis, resumable invoice sync, rate-limit handling, duplicate-invoice prevention, and observability/security. It includes links to current official Xero documentation and explicitly states its API assumptions.

## App API contract

### `GET /api/products/{id}`

Returns the seeded product, its two option dimensions, and SKU data. Each SKU contains a server-authoritative ID, price, stock, availability flag, media path, and option values.

- `200`: product payload
- `404 PRODUCT_NOT_FOUND`: unknown product

### `POST /api/cart/items`

Request:

```json
{
  "sku_id": "shell-graphite-m",
  "quantity": 2
}
```

Required header: `Idempotency-Key`.

- `201`: item reserved and added to cart
- `400 IDEMPOTENCY_KEY_REQUIRED` / `IDEMPOTENCY_KEY_INVALID`
- `404 SKU_NOT_FOUND`
- `409 SKU_UNAVAILABLE`, `INSUFFICIENT_STOCK`, or `IDEMPOTENCY_KEY_REUSED`
- `422 VALIDATION_ERROR`
- `500 INTERNAL_ERROR`

Error responses have this stable envelope:

```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "There is not enough stock for this quantity.",
    "details": { "available_quantity": 0 }
  }
}
```

### `GET /api/cart`

Returns cart rows, `total_item_count`, and `subtotal_cents`.

## Important app decisions

- The server never accepts a client price or stock value. It reads the SKU and rechecks stock in the same SQLite write transaction.
- `UPDATE skus ... WHERE stock >= quantity` is the final stock guard. `BEGIN IMMEDIATE` makes SQLite writes serial; a production relational database would use the same conditional update or an equivalent row lock.
- Idempotency records persist the canonical request hash and response. A repeated key/payload replays the original result; a key used for another payload produces a `409`.
- The UI keeps variant resolution in `src/variants.ts`, transport in `src/api.ts`, and screen state in `src/App.tsx`. It aborts/ignores stale product loads, derives disabled options from real SKU data, bounds quantity after variant/stock changes, and creates one idempotency key per add intent.

## Assumptions and limitations

- This exercise deliberately has one shared cart and no authentication or checkout. A production app would scope carts and idempotency records to a customer/session.
- SQLite is used for a zero-infrastructure submission. The schema and transaction design are intentionally portable to PostgreSQL.
- Product media is local seed data. No real customer data, credentials, tokens, or external-service calls are included.
- The product endpoint returns all SKUs because the domain is intentionally small. A larger catalogue should use cacheable product/availability APIs with inventory versioning.

## AI assistance disclosure

AI assistance was used to accelerate implementation and documentation. It was used for planning, code scaffolding, test-case brainstorming, the Xero review structure, and local product seed images. The submitted code was reviewed, adjusted, and executed locally: in particular, Task B was checked against brute force on randomized inputs; stock/idempotency behaviour was API tested; and the live frontend was exercised against the backend. I can explain the state models, dynamic-programming transition, transaction/idempotency design, and frontend state handling, and can modify them live.
