import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import requests


def choose_resolution(conflict: dict) -> str:
    existing = (conflict.get("existing_translation") or "").strip()
    new = (conflict.get("new_translation") or "").strip()
    term = (conflict.get("term") or "").strip()
    if existing:
        return existing
    if new:
        return new
    return term


def log_event(log_path: Path, payload: dict) -> None:
    event = dict(payload)
    event["logged_at"] = datetime.now().isoformat()
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--log-path", required=True)
    parser.add_argument("--poll-before-start", type=int, default=30)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    project_id = args.project_id
    log_path = Path(args.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    status_url = f"{base_url}/api/projects/{project_id}/translation-status"
    run_url = f"{base_url}/api/projects/{project_id}/translate-four-step"
    resolve_url = f"{base_url}/api/projects/{project_id}/resolve-conflict-live"

    session = requests.Session()

    for _ in range(max(args.poll_before_start, 0)):
        status = session.get(status_url, timeout=30).json()
        log_event(log_path, {"type": "status_poll", "status": status})
        if status.get("status") != "processing":
            break
        time.sleep(2)

    log_event(
        log_path,
        {
            "type": "client_start",
            "url": run_url,
            "project_id": project_id,
        },
    )

    with session.post(
        run_url,
        json={},
        stream=True,
        timeout=(30, None),
        headers={"Accept": "text/event-stream"},
    ) as response:
        response.raise_for_status()
        log_event(log_path, {"type": "http_status", "status_code": response.status_code})

        for raw_line in response.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip()
            if not line or not line.startswith("data:"):
                continue

            payload = line[5:].strip()
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                event = {"type": "raw", "payload": payload}

            log_event(log_path, event)
            if event.get("type") == "term_conflict":
                conflict = event.get("conflict") or {}
                body = {
                    "term": conflict.get("term") or "",
                    "chosen_translation": choose_resolution(conflict),
                    "apply_to_all": True,
                }
                resolved = session.post(resolve_url, json=body, timeout=30)
                response_payload = {}
                if resolved.content:
                    try:
                        response_payload = resolved.json()
                    except Exception:
                        response_payload = {"text": resolved.text}
                log_event(
                    log_path,
                    {
                        "type": "term_conflict_resolved",
                        "request": body,
                        "response_code": resolved.status_code,
                        "response": response_payload,
                    },
                )

            if event.get("type") in {"complete", "incomplete", "cancelled", "error"}:
                break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
