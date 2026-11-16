# Official OpenAI GPT-6.1 Sol

`gpt-6.1-sol` is an opt-in model on `openai-official`, direct to
`https://api.openai.com/v1`. Set server-only `OPENAI_API_KEY` in the shared `.env`.
No task, profile or phase default changes. Missing credentials fail closed.

The official transport uses Chat Completions, `max_completion_tokens`, and
`store: false`. Task/phase temperature inputs are deliberately not forwarded.
Both Chat Completions and Responses were live-probed successfully before this
integration; the implementation uses only Chat Completions. JSON mode was
verified through the real factory. Upstream model identity must match the
requested model, otherwise the generation fails. Logging includes model and
response ID, never prompts, upstream error bodies or credentials.

An explicit selection is isolated to the official provider, with at most one
transient retry of the same model. It neither falls back to Gemini/DeepSeek nor
becomes a fallback for existing models. Official OpenAI task methods reuse the
vendor-neutral prompt/parsing methods of the existing OpenAI-compatible class,
not that class's relay credentials, settings or generation transport.

Selection surfaces:
- Shared `/api/models` + `ModelSelector`: document/long-form, post, Slack.
- Post translation, optimization, hashtags and title keep the exact override.
- Long-form `model_overrides` supports every phase; no project is rewritten.
- Slack process/compose/refine/sync/optimize now consume the existing frontend
  model field instead of silently discarding it. Single-version editing also
  carries the selected model. Responses report model/provider metadata.
- Analysis/metadata task factories can use the explicit override; existing
  analysis endpoints without a model picker retain their previous defaults.
- CLI-agent model catalogs (Claude/Codex/Antigravity) are separate and unchanged.

Tests: `tests/unit/llm/test_openai_official.py`,
`tests/unit/api/test_slack_model_selection.py`,
`web/frontend/src/components/ModelSelector.test.tsx`.
Live acceptance uses short synthetic inputs only, not a user's saved project.
