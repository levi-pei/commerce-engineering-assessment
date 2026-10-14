# Commerce Engineering Assessment - Implementation Plan

## 1. Goal and submission shape

Build a review-ready repository that satisfies every stated requirement while keeping the implementation small enough to explain and modify live.

Repository layout:

```text
.
├── A/                  # Inventory reservation ledger (Python)
├── B/                  # Fulfilment split optimiser (Python)
├── C/                  # Xero integration review (Markdown)
├── app/
│   ├── backend/        # FastAPI + SQLite
│   └── frontend/       # React + TypeScript + Vite
├── README.md
└── PLAN.md
```

## 2. Design principles

- Prefer deterministic, explicit domain rules over framework magic.
- Validate complete commands/requests before mutating state.
- Treat retries as normal: event IDs and idempotency keys are first-class data.
- Keep API, domain logic, persistence, and UI state separate.
- Make failure states observable and testable, not only successful paths.
- Document assumptions, trade-offs, complexity, and AI assistance.

## 3. Work plan

### Phase 1 - Repository and contracts

- [x] Create the required folders and root documentation.
- [x] Record Python/Node versions and one-command setup/test instructions.
- [x] Define input/output examples and assumptions before implementation.
- [x] Add `.gitignore`, dependency manifests, and an AI-assistance disclosure.

### Phase 2 - Task A: Inventory Reservation Ledger

- [x] Model `on_hand`, per-order reservations, total reserved, and processed event IDs.
- [x] Parse and validate all command fields before applying a transition.
- [x] Implement `RESERVE`, `RELEASE`, `SHIP`, and `RESTOCK` in O(1) average time.
- [x] Mark well-formed rejected business events as processed; do not mark malformed input.
- [x] Return `OK`, `REJECTED`, or `DUPLICATE` plus current totals after each command.
- [x] Print remaining reservations sorted by `order_id`.
- [x] Test replay, malformed commands, insufficient stock, over-release/ship, zero initial stock, and mixed transitions.

### Phase 3 - Task B: Fulfilment Split Optimiser

- [x] Sort warehouses by ID to make tie-breaking deterministic.
- [x] Use dynamic programming over quantity, tracking the required comparison order:
  1. fewest warehouses;
  2. lowest total cost;
  3. lexicographically smallest sorted allocation list.
- [x] Avoid subset enumeration and external optimisation solvers.
- [x] Reconstruct the selected allocations and print them by warehouse ID.
- [x] Document time/space complexity and why the tie-break is correct.
- [x] Test impossible orders, zero-stock warehouses, fixed/unit-cost ties, lexicographic ties, and large quantities.

### Phase 4 - Task C: Xero Integration Review

- [x] Use current official Xero documentation and state the assumed API/SDK version.
- [x] Describe the smallest OAuth and tenant verification sequence.
- [x] Provide a 401/403/404 diagnostic decision tree.
- [x] Design resumable invoice sync with pagination, overlap windows, durable cursors, upserts, partial-failure handling, and safe replay.
- [x] Define 429 handling using response headers, exponential backoff with jitter, concurrency limits, retry budgets, and rescheduling.
- [x] Explain invoice-create deduplication and reconciliation after ambiguous timeouts.
- [x] Specify logs, metrics, alerts, correlation IDs, redaction, secret storage, and rotation.

### Phase 5 - Full-stack Variant PDP backend

- [x] Seed one product with colour and size options, at least six SKUs, one impossible combination, and one out-of-stock SKU.
- [x] Implement `GET /api/products/{id}`, `POST /api/cart/items`, and `GET /api/cart`.
- [x] Validate SKU, quantity, and stock entirely on the server; never trust client price/stock.
- [x] Persist stock, cart rows, and idempotency records in SQLite.
- [x] Use a transaction with an atomic conditional stock update to prevent overselling.
- [x] Store and replay the original add-to-cart response for repeated idempotency keys.
- [x] Return a consistent structured error envelope for validation, not-found, stock, conflict, and server errors.
- [x] Test success, validation, idempotency, and a concurrent final-unit race.

### Phase 6 - Full-stack Variant PDP frontend

- [x] Build a responsive product-detail experience for approximately 375 px and 1280 px widths.
- [x] Render product media, name, description, price, selected stock, quantity, and cart count.
- [x] Resolve variants from explicit domain functions and disable impossible/unavailable option values.
- [x] Prevent stale product responses from replacing newer state.
- [x] Keep quantity valid when the SKU changes.
- [x] Prevent duplicate clicks while adding and generate one idempotency key per user intent.
- [x] Handle loading, retry, incomplete selection, invalid combination, out-of-stock, progress, success, validation, insufficient stock, and server-error states.
- [x] Provide keyboard controls, visible focus, semantic labels, and `aria-live` feedback.
- [x] Add focused tests for variant resolution, quantity correction, and duplicate-click behaviour.

### Phase 7 - Delivery and verification

- [x] Run all Python and frontend tests from documented commands.
- [x] Run frontend type-check and production build.
- [x] Start both services and perform an end-to-end smoke test.
- [x] Verify the UI at mobile and desktop sizes, including error/loading states.
- [x] Audit the repository for secrets, personal data, generated junk, and hard-coded success paths.
- [x] Finalise README with architecture, API examples/status codes, assumptions, trade-offs, limitations, and test commands.

## 4. Intended technical choices

- Python 3.11+, FastAPI, Pydantic, SQLAlchemy/SQLite, pytest, and HTTPX.
- React, TypeScript, Vite, Vitest, Testing Library, and CSS modules or scoped plain CSS.
- SQLite is selected because it demonstrates durable idempotency and transactional stock safety without adding infrastructure.
- The backend remains a single process for the exercise, but correctness does not depend on an in-memory lock.

## 5. Acceptance checklist

- [x] `A/`, `B/`, `C/`, and `app/` exist and are independently understandable.
- [x] Setup commands work on a clean checkout.
- [x] All automated tests pass.
- [x] Requirements are demonstrated by behaviour, not screenshots.
- [x] No credentials, tokens, customer data, or machine-specific paths are committed.
- [x] Every important design choice can be explained and changed during review.
