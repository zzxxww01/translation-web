# Agent model selection and runtime updates

Goal: let users choose a concrete Claude/Codex model for each new conversation and retain that choice across resume/restarts.

Design: keep the provider buttons and add a model selector beside them. Read Codex's local model catalog and Claude's SDK initialization catalog without submitting an inference prompt. Always offer the server default, show discovery failures honestly, and allow a validated custom model ID. Store the requested model on the run; expose the runtime-reported model separately. Remember selections per agent and provider in the browser. Existing run metadata remains readable.

Implementation:
- [x] Add regressions for multipart model selection, durable resume, model discovery and malformed model IDs.
- [x] Add `skill_runner/models.py`, authenticated `/models/{harness}`, run metadata and session model forwarding. Codex commands use the per-run `-m`; Claude options use the per-run model before the environment default.
- [x] Add a compact model selector, per-agent/provider persistence and the selected/actual model in conversation headers. Exercise selection, provider changes and multipart payloads in frontend tests.
- [x] Add authenticated check/update endpoints and the web “工具与更新” dialog, with fixed verified installer commands, maintenance admission, version verification and honest failure states.
- [x] Run skill-runner tests (including SDK mapping), frontend tests, lint, TypeScript and production build.
- [x] Inspect production executable paths and perform the requested runtime upgrade. Codex 0.164.0 was already current; native Claude upgraded from 2.1.309 to 2.1.310. SDK 0.2.174 already bundles Claude 2.1.310. Versions verified on the server; credentials and run data preserved.
- [ ] Complete lifecycle review, push and pass Linux CI, deploy the exact reviewed revision, and smoke-test both providers through the web UI.

Runtime scope: user explicitly selected both a web check/update panel and the immediate server upgrade. Updates are restricted to stable official npm registry versions; Codex requires an owned, writable npm global install and Claude uses its native installer. Active, waiting, starting and queued work must block maintenance. Failed session closure must remain tracked for retries.

Production access: local SSH to wihu-server (43.153.22.116:42022) closes before key exchange, while server logs confirm SSH is healthy and user logins work. The existing authenticated web Agent provided server execution for diagnosis and the native Claude upgrade. Deployment remains pending until the reviewed code passes CI.

Validation baseline: 68 skill-runner tests passed, one SDK module skipped because the shared local Python environment does not have the SDK. Use an isolated dependency installation to exercise that module before completion. Changes are isolated from the user's dirty checkout in `feat/agent-model-picker`.

Local validation: skill-runner 139 tests (including SDK), frontend 135 tests, full ESLint and production build passed. Browser fixture verified model selection, persistence on reload, update progress and completion. Reviews found and fixed failed-close tracking and queued-Codex admission races with regressions. The broader Windows backend run had 1767 passing and 17 failures; all 17 also reproduce on untouched base 0171bc3 (POSIX wrappers, /proc paths and Windows GBK decoding). Linux CI is the deployment gate.
