import requests, json, time, pathlib
base='http://127.0.0.1:54321'
project='nvidia-broadcom-cpo-hbm4-lpddr6-tsmc-active-lsi-lo'
log=pathlib.Path('artifacts/manual-run-logs/live-status-validation.sse.jsonl')
log.write_text('', encoding='utf-8')
with requests.post(f'{base}/api/projects/{project}/translate-four-step', json={}, stream=True, timeout=(30, 7200)) as r:
    for raw in r.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith('data: '):
            continue
        payload=json.loads(raw[6:])
        with log.open('a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False)+'\n')
        if payload.get('type') == 'term_conflict':
            conflict=payload.get('conflict') or {}
            chosen=conflict.get('existing_translation') or conflict.get('new_translation') or conflict.get('term')
            requests.post(f'{base}/api/projects/{project}/resolve-conflict-live', json={
                'term': conflict.get('term'),
                'chosen_translation': chosen,
                'apply_to_all': True,
            }, timeout=60)
        if payload.get('type') in {'complete','incomplete','error','cancelled'}:
            break
