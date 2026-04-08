import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: monitor_translate_stream.py <base_url> <project_id> <log_path>",
            file=sys.stderr,
        )
        return 2

    base_url = sys.argv[1].rstrip("/")
    project_id = sys.argv[2]
    log_path = Path(sys.argv[3])
    log_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"{base_url}/api/projects/{project_id}/translate-four-step"
    started_at = datetime.now().isoformat()

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(
            json.dumps(
                {
                    "ts": started_at,
                    "kind": "client_start",
                    "url": url,
                    "project_id": project_id,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        log_file.flush()

        with requests.post(
            url,
            json={},
            stream=True,
            timeout=(30, None),
            headers={"Accept": "text/event-stream"},
        ) as response:
            log_file.write(
                json.dumps(
                    {
                        "ts": datetime.now().isoformat(),
                        "kind": "http_status",
                        "status_code": response.status_code,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            log_file.flush()
            response.raise_for_status()

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
                event["ts"] = datetime.now().isoformat()
                log_file.write(json.dumps(event, ensure_ascii=False) + "\n")
                log_file.flush()

                if event.get("type") in {
                    "complete",
                    "incomplete",
                    "cancelled",
                    "error",
                }:
                    break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
