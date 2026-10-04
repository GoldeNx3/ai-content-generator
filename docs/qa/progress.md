# QA implementation ledger
Plan: approved in conversation 2026-10-04.
- Existing checkout feat/queue; preserve user's uncommitted UI changes and implement in place so running Docker mounts use the changes.
- Deliverables: schema/scoring, queue/service/API, UI, full verification and real candidate 255 flow.
- Research basis: article's historical snapshot, never newer research.
- Trigger: manual, one tracked LLM call per attempt.
- No commits, publishing or automatic article fixes requested.

Completed:
- Migration 0006_article_qa applied to running database.
- Durable models, snapshot/hash binding, structured provider, scoring, service, queue/worker/API.
- UI report, statuses, issues, costs, readiness, version filtering and Jump to section.
- Review fixes: empty factual excerpts, overlapping claims, normalized noop edits, retry idempotency including concurrent replay, supplemental source evidence, informational conflict false positive, unmounted/stale UI refresh.
- Real candidate255 Research->Brief->Write yielded Article7/version3. QA report4 completed99, components100/100/94/100/100, supported46 unsupported0 critical0 warnings0 qa_passedtrue, cost0.098482USD.
- Live synthetic negative input from existing snapshot:39/100,unsupported5,criticalquote1,readinessfalse; all five markers detected without article edits.
- Verification:228 backend tests; npm test, lint, tsc; NODE_ENV=production build in Docker; UI and queue browser checks pass. Screenshots /tmp/content-qa-report.png and /tmp/content-qa-mobile.png.
- No commit, publication or automatic article fixes.
