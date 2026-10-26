# Antigravity and paragraph controls

Baseline: remote `origin/main` and live release `5dcbe4a278ddabd6701ce23e90d400d03a8d0f77`, verified 2026-10-27. Preserve original dirty local and server workspaces.

The user requested Antigravity CLI in the existing Agent page and help signing in. Add a third harness using the official `agy` executable, explicit conversation IDs, model selection, and the existing run/event/file interface. Use Google account sign-in; do not silently select API-key billing. Prepare the official OAuth flow and leave account authentication to the user's official login page.

Model choices come from installed runtimes: Codex's local catalog, Claude's SDK initialization, and `agy models` without inference. A manual refresh bypasses application caching where supported. Explain catalog provenance in the UI; listing a model does not guarantee quota or account access.

The continuous reading UI currently groups sentence fragments visually but still renders adoption controls per fragment. Move adoption to one control for the original paragraph, retaining existing missing-translation editing and draft protection. Move the reading bookmark from the upper left margin to a toolbar on the paragraph's top edge. Reveal on hover/focus, support touch, retain marked indication, and toggle the current mark off on a second click.

Implementation tasks:

1. Add Antigravity session/mapper and explicit harness dispatch, with targeted protocol/lifecycle tests.
2. Add dynamic Antigravity model discovery and frontend choice; make refresh and source labels accurate.
3. Refine paragraph/bookmark controls and focused editing/bookmark regressions.
4. Install the official CLI in the server user's directory, inspect supported authentication/update commands, and complete sign-in with user participation where required.
5. Review the combined changes, run targeted backend and frontend checks, then CI and deploy the exact merged revision using the existing release contract. Verify short Agent turns/resume and page controls. Do not retranslate a full article.

Official references: https://antigravity.google/docs/cli/headless/ , https://antigravity.google/docs/cli/reference/ , https://antigravity.google/docs/install?tab=cli .
