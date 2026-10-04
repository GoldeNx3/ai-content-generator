# Auto Fix + Approval — implementation ledger
Approved conversational plan, 2026-10-04.
- Preserve existing QA changes and live Docker workspace on feat/queue; no commits or resets.
- One fix attempt per click, automatic QA only; no-change result has no new version.
- Article row = version; no competing ArticleVersion table.
- Tasks: immutable versions/approval, patch validation/provider, transactional jobs, frontend, verification/live E2E/review.
- Backend: 254 tests green; API/model/queue/approval and append-only edits implemented.
- Frontend: lint/TypeScript/unit tests green; ui-check + dedicated auto-fix-ui-check green, all API mocked.
- Runtime migration 0007 applied. Public SvelteKit7 verified: all sources public svelte.dev.
- Auto-review initially rejected live export as potentially sensitive; after read-only public-source evidence, same E2E explicitly approved by auto-review. No workaround.
- Live: article8/v4 QA75, issue4 unsupported_claim; fix1 creates article9/v5, deletes only the fabricated sentence, ratio0.002276, cost0.027386. New QA queued; pending TPM retry.
- Remaining: section metadata refresh, final review, full verification/build, live final QA/approval audit, documentation.
- Final independent review: P1 re-QA must revoke invalid active approval; P2 selection-in-flight must disable approval actions. Both reproduced RED and fixed GREEN.
- Section metadata is rebuilt from actual Markdown (code fences protected); per-issue failed results persisted on terminal errors.
- Live completed: article8/v4 QA75 -> fix1 -> article9/v5 QA99 -> approved. Only change removed fabricated editor claim; immutable source/hash verified. POST fix202 in0.048s; editor cost0.027386, successor QA0.077548. Queue handled TPM retries successfully.
- Final backend run257 green before added checkpoint/iteration regression cases; frontend lint/types/unit tests green; dedicated browser including approval selection-race green. Production build passed, final repeat due UI guard change pending.
- Completion verification: backend260 passed (15.72s); frontend lint, TypeScript and unit tests passed; ui-check, queue-ui-check and dedicated auto-fix-ui-check passed; production build passed. git diff --check clean.
- Independent review's P1/P2 both fixed with observed RED->GREEN regressions. No deferred important findings.
