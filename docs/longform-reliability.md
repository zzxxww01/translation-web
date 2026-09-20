# Long-form translation reliability acceptance

This checklist distinguishes a delivered file from a complete translation.

## Acceptance cases

- Render the actual section-title prompt, including glossary/context variables, before any network call. Template errors must fail a regression test rather than become English "translations".
- A failed title remains pending. A later resume retries unchanged English prose titles but preserves legitimate product/model names and user-edited Chinese titles.
- Exercise the public provider factory used by each long-form phase, not only the fallback adapter in isolation. Inject an empty response and transient failure, then verify bounded retries/routing and eventual success or explicit failure.
- Explicit official selectors remain official. Normal routing prefers relay providers. Neither route may leak credentials to diagnostics.
- Preserve the caller's timeout and bound total work. Permanent errors must not burn the retry budget; SDK retries must not multiply application retries unexpectedly.
- A real empty response records one failed call with its returned token usage, not a successful translation or two calls.
- Missing title/body translations appear in the export QA report with locations and counts. Images, metadata and legitimate names are not missing prose.
- Normal Chinese export must not silently represent an incomplete document as finished. An explicit one-time override may download an unfinished draft, with a visible warning; the next export checks again. English source export remains available.
- Resume and deployment must preserve confirmed translations, manual edits and persisted checkpoints. Do not rerun all paid translations merely to verify routing.

## Runtime boundaries

- Retry limits apply per generation, not per document: at most four adapter attempts, with at most two per route. A request timeout remains a per-attempt timeout, not a document-wide deadline.
- Built-in configured routes reserve capacity for an official fallback; legacy/custom constructors retain their parameters and cannot invent an unconfigured alternate provider.
- Protected standalone names use the same predicate in title validation and export coverage. This is structural completeness checking, not proof of semantic translation quality.
- Synchronous title-provider calls run in worker threads so they do not block the API event loop. Persistence and compare-and-set checks remain in the async service after the call returns.

## Rollout checks

1. Back up source/build artifacts and record hashes of persisted section metadata.
2. Run backend and frontend regression suites and production build.
3. Review actual production/integration differences; deploy only scoped fixes and required dependencies, not unrelated remote changes.
4. Confirm no active translation before service restart.
5. Verify local/public health, the actual export endpoint, browser warning/override interaction and one short real provider call.
6. Recheck section metadata hashes. Report test-injected failure recovery separately from live upstream-call results.
