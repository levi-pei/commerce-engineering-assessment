# Task C - Xero Integration Review

## Assumptions

- This design targets Xero Accounting API v2 over HTTPS in October 2026 and uses raw HTTP terminology so it is independent of SDK release cadence.
- The service uses OAuth 2.0 Authorization Code flow with offline access, and each internal organisation is explicitly mapped to one Xero `tenantId`.
- Background jobs are at-least-once. PostgreSQL-like transactional semantics are assumed for production persistence.

## C1 - Connection verification

Use the smallest read-only sequence below before requesting invoices:

1. Load the organisation's encrypted token set and mapped `tenantId`. Refresh the access token if it will expire during this job. A successful refresh proves the refresh token, client credentials, and token endpoint are valid; failure stops the job before business API calls.
2. Call `GET https://api.xero.com/connections` with `Authorization: Bearer <access_token>`. A `200` proves that the access token is accepted. Find exactly one `ORGANISATION` entry whose `tenantId` equals the stored mapping; this proves the user granted this app access to the intended organisation and avoids silently selecting the first tenant.
3. Make one cheap Accounting API read with that exact `Xero-tenant-id`, for example `GET /api.xro/2.0/Organisation`. A `200` with the expected organisation identity proves tenant-scoped Accounting API access and the required scopes. Only then start invoice pagination.

Store both `connectionId` and `tenantId`, but send `tenantId` in Accounting API requests. Never infer tenant selection from array order or a tenant name.

Reference: [OAuth 2.0 overview](https://developer.xero.com/documentation/guides/oauth2/overview), [Xero tenants and connections](https://developer.xero.com/documentation/guides/oauth2/tenants/), [managing tokens and IDs](https://developer.xero.com/documentation/best-practices/data-integrity/managing-tokens/).

## C2 - Failure diagnosis

Start by logging status, endpoint template, internal organisation ID, tenant ID hash, job ID, attempt, and Xero correlation ID. Do not log tokens or invoice payloads.

```text
connections succeeds
  |
  +-- invoices = 401
  |     refresh once under a per-connection lock
  |       +-- succeeds -> retry once with the new access token
  |       +-- invalid_grant/revoked -> mark connection ACTION_REQUIRED
  |       +-- still 401 -> verify audience/token environment and stop retrying
  |
  +-- invoices = 403
  |     compare granted scopes with accounting.transactions/accounting.transactions.read
  |     verify the connecting user still has invoice permissions in this organisation
  |     verify production credentials and consent belong to the same Xero app
  |     -> require re-consent or permission repair; automatic retry will not help
  |
  +-- invoices = 404
        verify base URL, Accounting API v2 path, method, and resource identifier
        confirm Xero-tenant-id exactly matches a current /connections tenantId
        compare sandbox/demo vs production configuration and selected organisation
        -> correct configuration/resource; do not treat it as an empty invoice set
```

For every branch, reproduce with the same endpoint and redacted headers outside the worker, compare a working environment's app ID, scopes, base URL, and tenant mapping, and inspect the structured response body. Never switch tenant IDs speculatively.

Reference: [Accounting API response codes](https://developer.xero.com/documentation/api/accounting/responsecodes), [Xero tenants](https://developer.xero.com/documentation/guides/oauth2/tenants/).

## C3 - Incremental synchronisation

Maintain one durable sync state per `(internal_organisation_id, resource_type)`:

```text
committed_modified_since_utc
current_run_id
current_page
run_started_at_utc
status / last_error
```

Algorithm:

1. Acquire a per-tenant invoice-sync lease so two workers cannot advance the same cursor concurrently.
2. Set `run_started_at` from the database clock. Request invoices using `If-Modified-Since = committed_cursor - overlap` (for example five minutes), ordered consistently, with `page=1`.
3. Read every page. Xero returns 100 invoices per page when pagination is used; continue until a short/empty page. Upsert each invoice by `(tenant_id, InvoiceID)` inside a transaction, including its Xero update timestamp and deletion/void status.
4. Commit each page and its page checkpoint together. Reprocessing a page is safe because the database write is an upsert and child rows use stable Xero IDs or are replaced transactionally.
5. If a page or transform fails, record the page/error and leave the committed high-water mark unchanged. Retry the page for transient failures; quarantine a permanently invalid record with an alert rather than silently skipping it.
6. Only after all pages succeed, atomically advance `committed_modified_since_utc` to `run_started_at`. The overlap intentionally re-reads boundary updates and protects against clock precision, pagination changes, and late commits.

This is at-least-once ingestion with idempotent storage. A periodic full reconciliation (for example weekly) detects missed updates, deleted mappings, and drift. Cursor state is never advanced from the largest timestamp merely observed in a partial page.

Reference: [Accounting API invoices and `If-Modified-Since`](https://developer.xero.com/documentation/api/accounting/invoices), [efficient data retrieval](https://developer.xero.com/documentation/best-practices/api-call-efficiencies/efficient-data-retrieval/).

## C4 - Rate limits

On HTTP `429`:

- Read `Retry-After` and `X-Rate-Limit-Problem`; schedule the job no earlier than that delay. Add small random jitter so many workers do not wake together.
- If the header is missing or invalid, use capped exponential backoff with full jitter. Do not sleep while holding a worker or database transaction; release the job back to the delayed queue.
- Enforce per-tenant concurrency below Xero's five-call concurrent limit and a global application limiter. Feed `X-MinLimit-Remaining`, `X-DayLimit-Remaining`, and `X-AppMinLimit-Remaining` into proactive throttling.
- Give each job a retry budget by attempt count and elapsed age. When exhausted, move it to a dead-letter/action queue and alert with correlation IDs.
- Prioritise interactive and token-refresh work over bulk backfills; batch supported writes and spread non-urgent syncs across the day.

Retry timeouts, connection resets, `429`, and selected `5xx` responses. Retry `401` only once after coordinated refresh. Do not automatically retry validation/conflict `400`, permission/scope `403`, genuine `404`, or other deterministic business errors until their cause changes.

Reference: [Xero rate limits and response headers](https://developer.xero.com/documentation/best-practices/api-call-efficiencies/rate-limits/).

## C5 - Data integrity

Use a transactional outbox and a durable operation record keyed by `(tenant_id, internal_order_id, operation_type)`. It stores a canonical request hash, a stable Xero idempotency key, state (`PENDING`, `SENT_UNKNOWN`, `CONFIRMED`, `FAILED`), attempts, and the resulting `InvoiceID`.

Before sending, reserve a deterministic internal invoice number/reference containing the immutable order ID. Send the same payload and the same `Idempotency-Key` for retry attempts. Xero caches idempotent mutation responses, but currently documents a six-minute key lifetime, so local uniqueness remains the long-term guard.

After a timeout, mark the result `SENT_UNKNOWN`; do not immediately create again. First reconcile by known `InvoiceID`, otherwise query by the reserved invoice number/reference and verify tenant, contact, currency, totals, and line-item fingerprint. If one exact match exists, record its `InvoiceID` and confirm the operation. If none exists and the retry is still inside the idempotency window, retry with the same key. Outside that window, require a completed reconciliation before creating with a new key. Multiple/conflicting matches go to manual review and block further creation.

A database unique constraint on the internal operation key prevents two local workers from initiating the same invoice. The mapping from internal order to Xero `InvoiceID` is also unique per tenant.

Reference: [Xero idempotent requests](https://developer.xero.com/documentation/guides/idempotent-requests/idempotency/).

## C6 - Observability and security

Structured logs:

- job/run ID, attempt, internal organisation ID, resource, page, item count, duration, outcome, retry decision;
- HTTP method, endpoint template, status, Xero correlation ID, rate-limit headers, and a one-way tenant ID hash;
- cursor before/after, overlap window, records inserted/updated/quarantined, and reconciliation result.

Metrics and alerts:

- request count/latency/errors by endpoint and status; `401`, `403`, `404`, `429`, and `5xx` rates;
- remaining minute/day quota, queue depth/age, retries, dead letters, token-refresh failures;
- sync lag, run duration, cursor age, pages/items processed, duplicate/upsert count, reconciliation mismatches;
- alerts for revoked credentials, sustained auth errors, quota exhaustion risk, old cursors, repeated partial failures, dead letters, and possible duplicate invoices.

Correlation:

- propagate an internal trace ID through job, HTTP request, database writes, and logs;
- retain the Xero correlation ID returned by the API;
- use operation ID and internal order ID to join create/reconciliation events without exposing customer data.

Never log access/refresh tokens, client secrets, authorisation codes, `Authorization` headers, cookies, full request/response bodies, bank/tax details, customer addresses, or unnecessary invoice descriptions. Redact centrally and allowlist fields rather than relying on individual callers.

Store client secrets and token encryption keys in a managed secret/KMS service. Store refresh/access tokens encrypted at rest with tenant-bound authenticated encryption; restrict decryption to the worker identity and audit access. Rotate client secrets and encryption keys with overlap/versioning, re-encrypt tokens gradually, serialise refreshes per connection, atomically replace rotated refresh tokens, and provide a revocation/re-consent path. Use TLS everywhere and least-privilege OAuth scopes.
