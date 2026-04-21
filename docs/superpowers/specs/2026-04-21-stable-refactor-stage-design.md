# Stable Refactor Stage Design

Date: 2026-04-21
Project: Translation Agent
Scope: Stable refactor stage covering engineering baseline repair and the first backend architecture split without changing product behavior or UI.

## Goals

This stage aims to move the project from "feature-rich but structurally fragile" to "stable enough for continuous refactoring." The work must preserve all user-visible functionality and existing UI while reducing operational risk, restoring test signal, and creating clearer backend boundaries for later stages.

The stage ends when the following are true:

- Startup and runtime configuration behavior is centralized and predictable.
- The test suite can at least be collected without structural import errors.
- Known runtime bugs in conflict resolution and resource cleanup are fixed.
- The longform translation backend has a clearer orchestration boundary, with the first extraction of run/session responsibilities out of the main service and router.
- Existing endpoints and frontend behavior remain compatible.

## Non-Goals

This stage does not attempt to fully complete the overall refactor.

Specifically out of scope:

- Full replacement of the current project storage layout.
- Full decomposition of `ProjectManager`.
- Full decomposition of `GeminiProvider`.
- Frontend-wide state architecture redesign.
- UI redesign, feature changes, or endpoint contract changes unless needed to preserve existing behavior.
- Aggressive repository cleanup that risks removing user-relevant artifacts without confirmation.

## Problems Being Solved

### 1. Configuration boundary drift

Configuration is currently validated in more than one place, and different layers read environment variables directly. This creates conflicting startup rules and makes deployment behavior hard to reason about.

### 2. Unreliable engineering baseline

The current test suite includes outdated imports and stale test files that fail during collection. This means the suite does not clearly distinguish active regressions from historical debris.

### 3. Runtime correctness issues

There are confirmed code-level defects in:

- live terminology conflict resolution flow
- `WechatFormatter` executor cleanup
- longform translation state management relying on shared mutable globals

### 4. Translation backend over-centralization

`BatchTranslationService` currently acts as orchestration layer, state registry, artifact writer, analysis/glossary seed layer, and section execution coordinator. This makes safe changes expensive and increases the probability of regressions.

### 5. Router-level orchestration leakage

The longform translation router performs SSE streaming, thread/event bridging, cancellation coordination, and conflict handling directly. This is too much infrastructure logic for an API layer.

## Recommended Approach

Use a conservative phased refactor with compatibility adapters.

Why this approach:

- The project already has many interacting features and partial test coverage.
- A big-bang rewrite would likely break translation flows and make regressions difficult to isolate.
- The project needs a stable platform for future refactor stages more than it needs maximal structural purity in one pass.

The implementation should favor extraction over rewrite:

- move responsibilities into focused modules
- keep current API and call paths working through adapters
- verify behavior after each batch

## Alternatives Considered

### Alternative A: Big-bang backend rewrite

Replace `BatchTranslationService`, router orchestration, and project persistence boundaries in one large pass.

Rejected because:

- the current test baseline is not strong enough to support it
- rollback would be expensive
- unrelated regressions would be difficult to attribute

### Alternative B: Baseline-only cleanup

Fix tests, configuration, and runtime bugs, but postpone architectural extraction.

Rejected because:

- it improves reliability but leaves the highest maintenance cost unchanged
- it would not materially advance the "complete refactor" goal the user requested

## Stable-Stage Scope

This stage contains two work bands.

### Band 1: Baseline repair

- centralize startup configuration validation
- reduce direct `os.getenv` branching in runtime-critical paths
- restore `pytest --collect-only` success
- fix stale imports and clearly obsolete tests
- fix the live conflict resolution bug
- fix `WechatFormatter` cleanup ownership
- reduce repository noise where it directly hurts engineering clarity

### Band 2: First backend architecture split

- extract translation run state ownership from `BatchTranslationService`
- extract translation artifacts persistence from `BatchTranslationService`
- extract SSE/stream execution coordination from the translation router
- keep endpoint contracts unchanged
- keep cancellation and progress semantics compatible with existing frontend flows

## Target Architecture After This Stage

### Configuration

Introduce a single startup validation path.

Expected boundary:

- `src/settings.py` or a dedicated config bootstrap module owns required-setting validation
- application startup imports validated settings instead of re-validating ad hoc
- business modules may still read non-critical environment toggles during transition, but critical provider rules must come from one source

### Translation runtime

Introduce explicit translation run ownership.

Expected boundary:

- `BatchTranslationService` remains the public service entrypoint for compatibility
- a new run-oriented module owns active run tracking, cancellation state, and run metadata lifecycle
- a new artifact-oriented module owns run directory creation and JSON artifact persistence

### Router orchestration

Expected boundary:

- router validates request and returns `StreamingResponse`
- stream/session helper owns queueing, heartbeat, disconnect cancellation, and background execution bridging
- live conflict event coordination becomes explicit and testable

## Proposed Module Extractions

These names are recommendations, not hard requirements, but the boundary intent is fixed.

### 1. `src/services/translation_run_registry.py`

Responsibilities:

- active run registration
- cancellation intent tracking
- retrieval of current run state
- release semantics

Must not do:

- translation work
- artifact writing
- prompt construction

### 2. `src/services/translation_artifact_service.py`

Responsibilities:

- create run artifact directories
- normalize and write JSON artifacts
- load prior analysis/run summaries when needed

Must not do:

- manage cancellation state
- mutate project/domain objects beyond artifact persistence

### 3. `src/api/streaming/translation_stream_session.py`

Responsibilities:

- bridge background translation execution with SSE output
- manage progress queue
- manage heartbeats
- request cancellation when the client disconnects
- coordinate live term conflict wait/resolve flow

Must not do:

- own translation business logic
- read/write project data directly

### 4. Compatibility adapters inside existing modules

`BatchTranslationService` and `translate_projects.py` should be slimmed by delegation rather than rewritten at once.

## Detailed Implementation Sequence

### Step 1: Repair engineering baseline

1. Centralize settings validation.
2. Remove duplicate app-startup provider requirements from the FastAPI entrypoint.
3. Restore test collection by fixing stale imports and isolating obsolete tests.
4. Fix the confirmed conflict-resolution variable bug.
5. Fix `WechatFormatter` cleanup lifecycle.
6. Run collection, lint, and targeted smoke checks.

### Step 2: Extract run-state ownership

1. Create `translation_run_registry`.
2. Move active-run and cancellation bookkeeping out of class-level service state.
3. Keep current service methods calling into the new registry.
4. Preserve existing progress and cancellation responses.

### Step 3: Extract artifact ownership

1. Create `translation_artifact_service`.
2. Move run artifact helpers out of `BatchTranslationService`.
3. Keep file naming and artifact schema unchanged in this stage.

### Step 4: Extract streaming/session coordination

1. Create a stream/session helper under API infrastructure.
2. Move background-task execution, queue polling, heartbeat, disconnect handling, and conflict wait/wake flow out of the router.
3. Keep current endpoint paths and event payload formats unchanged.

### Step 5: Stabilize and verify

1. Re-run collection and lint.
2. Add or adjust tests for:
   - conflict resolution flow
   - cancellation behavior
   - stream/session helper
   - `WechatFormatter` cleanup path
3. Confirm the frontend contract is unchanged.

## Data and API Compatibility Rules

The following are hard requirements for this stage:

- no route path changes
- no request/response schema changes unless required to fix a current bug and still remain backward-compatible
- no UI changes
- no new required environment variables
- no changes to persisted artifact schema unless the previous schema is retained as-is

## Risk Management

### Primary risk: hidden coupling in translation flow

Mitigation:

- extract one responsibility at a time
- keep old entrypoints delegating to new helpers
- add targeted tests before deeper cleanup

### Primary risk: cancellation/progress regressions

Mitigation:

- preserve current event types and payload shapes
- keep cancellation semantics compatible with the existing frontend service
- verify disconnect and heartbeat behavior after stream extraction

### Primary risk: breaking ad hoc deployment workflows

Mitigation:

- avoid changing startup commands
- keep `.env` variable names unchanged
- only centralize validation, not rename settings

## Testing Strategy

Minimum acceptance checks for this stage:

- `pytest --collect-only -q` passes
- targeted backend tests for stream/conflict/cancellation paths pass
- frontend lint runs without new warnings introduced by this stage
- any edited backend modules have at least focused regression coverage where practical

Where full test green is not immediately achievable because of unrelated pre-existing failures, the final report must clearly separate:

- fixed structural failures
- remaining pre-existing failures
- new risks introduced by the refactor, if any

## Deliverables

At the end of this stage, the repository should contain:

- a written design spec
- centralized configuration validation
- repaired test collection baseline
- fixed conflict-resolution and cleanup bugs
- extracted translation run registry
- extracted translation artifact service
- extracted translation stream/session helper
- slimmer `BatchTranslationService`
- slimmer translation router
- verification notes

## Acceptance Criteria

This stage is complete when:

1. The application still exposes the same user-facing functionality and UI behavior.
2. `pytest --collect-only -q` succeeds.
3. The live conflict resolution path no longer contains the current broken variable reference.
4. `WechatFormatter` no longer throws executor cleanup errors due to class/instance mismatch.
5. `BatchTranslationService` no longer owns all run-state and artifact responsibilities directly.
6. The translation router no longer directly owns the full SSE execution lifecycle.
7. The codebase is in a more stable state for the next refactor stage, which will target deeper `ProjectManager`, LLM-layer, and frontend decomposition.

## Next Stage Preview

The next stable stage after this one should target:

- `ProjectManager` decomposition into repository/export/recovery boundaries
- deeper LLM layer cleanup
- frontend orchestration decomposition for document workflows

This next stage is intentionally not included now to keep the current stage bounded and finishable.
