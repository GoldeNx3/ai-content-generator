# Auto Fix + Approval

Article row ID is a concrete version ID. Auto Fix and edits append rows; no old title,
lead, content or SEO is overwritten. Generated/regenerated versions start a new
iteration lineage; manual edits retain the consumed fix budget.

## Flow

Choose a version in QA (same selection as Write). Run QA. For eligible findings,
click **Auto Fix · płatne**. One click runs one editing request. Run QA of the new version separately.
The queue runs independently of the browser. The fix report includes fixed/skipped/
failed per issue, costs, change ratio and literal Before/After changes. A changed
result creates a new current version and queues QA atomically. All-skipped/no-change
results preserve the original and require manual review without another paid QA.

Only a current passing QA can produce ready_for_approval. Approve/Reject act on the
selected version; approving supersedes the former approved version of the candidate.
Warnings do not block approval. A negative re-QA revokes active approval but retains
its historical timestamp. A real manual edit creates a draft requiring a new QA.

The same existing version selector and workflow style are used. Visual cards are:
1 RSS, 2 classification, 3 research, 4 Brief+Write, 5 QA, 6 Auto Fix+Approval.
The logical pipeline stage is 7, because Brief and Write share a card.

## Configuration

- OPENAI_AUTO_FIX_MODEL: configured editor; blank falls back to Writer.
- AUTO_FIX_MAX_CHANGE_RATIO=0.35: warning threshold, not a structural-change veto.
- AUTO_FIX_MAX_ITERATIONS=2: completed attempts across the version ancestry, including
  all-skipped attempts. Technical retries of the same job do not consume another.
- AUTO_FIX_TIMEOUT_SECONDS=300; JOB_AUTO_FIX_ARTICLE_TIMEOUT_SECONDS=900.
- QA_PASS_SCORE remains the approval threshold (default85).

Auto Fix uses only the frozen research/brief of the selected version. No source
fetching, web tools or keyword API are wired into its provider. The configured LLM
gets literal patch instructions and Pydantic structured output. Unknown IDs,
ambiguous/overlapping patches, unlinked changes and ungrounded added numbers fail
validation. Numeric/date corrections require cited research evidence. Successor QA
checks semantic correctness; approval stays unavailable until it passes.

Ignored conflicts and missing uncertainties are kept for human review. Unsupported
quotes/names and contradictions are also outside this MVP's automatic policy.

## API

- POST /api/article-versions/{id}/auto-fix, optional {"issue_ids":[41,42]} ->202 JobRead.
- GET /api/article-fixes/{id} and GET /api/article-versions/{id}/fixes (outgoing and
  incoming fix history).
- POST /api/article-versions/{id}/approve.
- POST /api/article-versions/{id}/reject, optional {"reason":"..."}.
- PATCH /api/articles/{id} now returns a new version when editable fields change.
  Normalized no-op edits return the same version. Clients must use the returned ID.
- Legacy status endpoint cannot bypass QA or set readiness/approved arbitrarily.

Jobs use auto_fix_article, the existing candidate mutex, idempotency keys, attempt
history, checkpointed LLM results, lease fencing and retry/recovery. Final child,
fix results, finished editor job and pending QA report/job are one transaction.
An interrupted or failed transaction does not leave an orphan child version.

Migration0007 is additive. Existing hashes are backfilled, valid QA readiness is
retained, and older duplicate approved versions become superseded. Downgrade is
explicitly disabled rather than silently deleting version/fix history.

## Verification

Backend tests cover the requested factual/editorial cases, strict IDs/output,
immutable versions, approval races, re-QA revocation, iteration inheritance,
transaction rollback, known cost on invalid output, terminal issue failures,
expired leases and checkpoint reuse. Browser tests mock all API calls (no paid
traffic): ui-check.mjs, queue-ui-check.mjs, auto-fix-ui-check.mjs.

Paid live check is opt-in:
`docker compose exec -T api python -u -m tests.auto_fix_live_check 7`
It appends a clearly fabricated claim to a test child of the public SvelteKit
article, then explicitly starts QA -> Auto Fix -> QA of the new version -> internal approval. It does
create durable versions and incur LLM costs; it never publishes.

Verified 2026-10-04: source article8/v4 got75 with one unsupported claim. Fix1
created article9/v5 by deleting only that sentence (change ratio0.002276), successor
QA got99 with0 critical/unsupported and the version was approved. Costs: editor
$0.027386; successor QA$0.077548. Original content/hash stayed unchanged. All six
research sources were public svelte.dev. Editor/QA used configured gpt-4.1.

Final regression:260 backend tests passed; frontend unit tests, lint, TypeScript,
production build and all three browser suites passed. Independent review findings
(negative re-QA approval revocation and selection-in-flight decision guard) have
regression tests and are fixed.
