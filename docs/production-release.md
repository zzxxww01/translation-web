# Production release contract (momo.beauty)

Production must serve one tested Git revision, not a development checkout plus a separate backend.

## Authoritative paths

- Source repository: `https://github.com/zzxxww01/translation-web`
- Original dirty workspace: `/home/zxw/translation-agent` — preserve it; never build into its `dist` for production.
- Immutable release directories: `/home/zxw/releases/translation-agent-<revision>`.
- Active pointer: `/home/zxw/releases/translation-agent-current`.
- User service: `translation-agent-live.service`, persistent unit under `~/.config/systemd/user/`.
- Both service WorkingDirectory and Nginx SPA/assets roots use the active pointer.
- `.env`, `projects`, `glossary`, `glossary_new`, `data`, `logs` are explicitly linked to existing production locations. Do not copy or replace these with tracked example data.
- Claude terminal demo has its own Nginx include; preserve it during translation deployments.

## Safe release sequence

1. Inspect `systemctl --user show ... -p WorkingDirectory -p MainPID` and the actual Nginx site. Fetch remote main and create a clean worktree; never reset/stash the original dirty workspace.
2. Back up frontend artifacts, Nginx/unit files, dirty source patches and business data to `/home/zxw/backups`. Use SQLite Backup API if databases exist. Never commit secrets or business data.
3. Integrate fixes on remote main and test backend, frontend unit tests, lint, typecheck and production build using the pinned dependencies. Push normally, wait for CI, merge without force. Use that exact merged commit for the release.
4. Create the release worktree. Archive its tracked seed runtime directories before replacing them with links to production data; never delete existing user data. Install the release's Python dependencies into its own `.venv` and frontend dependencies with `npm ci`. The historical `requirements-lock.txt` is only a partial constraint set, not a complete dependency lock: do not `uv pip sync` it. Use `uv pip install -r requirements.txt -c requirements-lock.txt`, or freeze the already-tested complete environment into release-local `runtime-requirements.txt` and sync that full snapshot. Require both `uv pip check` and a successful app import before stopping production, then run tests using the new interpreter in an isolated test worktree. Chain these gates with fail-fast logic, never semicolons that continue into deployment after a failed import.
5. Build frontend **inside this release** and create `web/frontend/dist/release.json` containing its complete Git `revision`. Do not rebuild in the old dirty workspace. Nginx must send `no-cache` for index and release metadata; only content-hashed assets are immutable.
6. Check each project's `/api/projects/{id}/translation-status`; `can_stop`, `active_run_id`, `active_project_id` must show no active work. Do not infer activity from the project's review/approval status or `/api/tasks` (that endpoint is a todo list). Do not cancel active paid work automatically. Pause deployment if work is active. Immediately before restart, take another snapshot of business files, verify no active task and stop gracefully.
7. Atomically change the active symlink, validate Nginx (`nginx -t`), reload it and restart the managed backend. Restart only when required; do not launch a second unmanaged process on 54321. The persistent user unit must be enabled, with user linger configured. Keep the old release for rollback.
8. Run `python3 scripts/verify_release.py --release /home/zxw/releases/translation-agent-current`. It checks actual process cwd, primary Nginx roots, public revision, entry HTML and asset hashes, and health. Failure is a failed deployment, not a warning to ignore.
9. Exercise real short post translation, coherence optimization, and title generation. Every returned title must have `len(title) <= 20` Unicode code points; do not claim valid lengths from HTTP 200 alone. Verify browser output and preserved project/data counts and hashes. Mocked tests do not prove providers work.
10. Record exact commit, backup paths, test outcomes and public URL. If any fixture created data, remove only those fixture records. Original worktree remains unchanged and non-authoritative.

## Rollback

With no active work, repoint the active symlink to the previous release, restart the same user service, validate/reload Nginx if its configuration changed, and re-run the release gate against the prior manifest. Restore backed-up config when reverting the first migration to this layout. Never restore business data merely to roll back code: that can discard edits made after deployment.

A named Nginx fallback for old hashed asset URLs can serve prior dist files to already-open tabs; it must never be the primary SPA root. Keep primary roots first and aligned. Stale browsers may still send legacy `coherence`; backend compatibility remains required even after new frontend deployment.
