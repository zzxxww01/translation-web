import json
import pathlib
import sys
import requests

base = sys.argv[1]
project = sys.argv[2]
log_path = pathlib.Path(sys.argv[3])
model = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
payload = {'model': model} if model is not None else {}
log_path.parent.mkdir(parents=True, exist_ok=True)
log_path.write_text('', encoding='utf-8')
summary_path = log_path.with_suffix('.summary.json')
summary = {
    'project': project,
    'endpoint': f'{base}/api/projects/{project}/translate-four-step',
    'events': 0,
    'terminal_event': None,
}
with requests.post(summary['endpoint'], json=payload, stream=True, timeout=(30, 7200)) as response:
    summary['http_status'] = response.status_code
    if response.status_code >= 400:
        summary['error_body'] = response.text
    response.raise_for_status()
    for raw in response.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith('data: '):
            continue
        data = json.loads(raw[6:])
        with log_path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(data, ensure_ascii=False) + '\n')
        summary['events'] += 1
        if data.get('type') == 'term_conflict':
            conflict = data.get('conflict') or {}
            chosen = conflict.get('existing_translation') or conflict.get('new_translation') or conflict.get('term')
            requests.post(
                f'{base}/api/projects/{project}/resolve-conflict-live',
                json={
                    'term': conflict.get('term'),
                    'chosen_translation': chosen,
                    'apply_to_all': True,
                },
                timeout=60,
            ).raise_for_status()
        if data.get('type') in {'complete', 'incomplete', 'error', 'cancelled'}:
            summary['terminal_event'] = data.get('type')
            summary['terminal_payload'] = data
            break
summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
