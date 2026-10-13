"""Sessions must retain the actual terms and serialize read/modify/write operations."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest

from src.models.terminology import Term
from src.services.translation_session_service import TranslationSessionService


class MemoryTerms:
    def __init__(self, root):
        self.base_path = root
        self.rows = {'global': [Term.create('cache', '缓存', 'global')], 'project': []}
        self.reads = 0
    def load_terms(self, scope, project_id=None):
        self.reads += 1
        return [row.model_copy(deep=True) for row in self.rows[scope]]


@pytest.fixture
def service(tmp_path):
    return TranslationSessionService(MemoryTerms(tmp_path))


def test_snapshot_keeps_definitions_when_active_glossary_changes(service):
    session = service.create_session('demo')
    service.storage.rows['global'][0].translation = '高速缓存'
    frozen = service.get_session_terms(service.load_session(session.id))
    assert frozen[0].translation == '缓存'
    frozen[0].translation = 'mutated returned object'
    assert service.get_session_terms(session)[0].translation == '缓存'


def test_detects_same_id_translation_and_strategy_changes(service):
    session = service.create_session('demo')
    term = service.storage.rows['global'][0]
    term.translation = '高速缓存'
    term.strategy = 'first_annotate'
    changes, changed = service.detect_term_changes(session.id)
    assert changed
    assert [(c.term_id, c.change_type) for c in changes] == [(term.id, 'modified')]
    assert changes[0].old_value['translation'] == '缓存'
    assert changes[0].new_value['translation'] == '高速缓存'
    service.refresh_snapshot(session.id)
    assert service.get_session_terms(service.load_session(session.id))[0].translation == '高速缓存'
    assert service.detect_term_changes(session.id) == ([], False)


def test_snapshot_survives_term_deletion_without_repeated_store_scans(service):
    for i in range(30):
        service.storage.rows['global'].append(Term.create(f'word{i}', '译法', 'global'))
    session = service.create_session('demo')
    service.storage.rows['global'] = []
    service.storage.reads = 0
    assert len(service.get_session_terms(session)) == 31
    assert service.storage.reads == 0


@pytest.mark.parametrize('identifier', ['../outside', '/tmp/outside', '..\\outside', 'a/b', '', 'C:outside', 'bad\x00id'])
def test_session_id_cannot_escape_storage(service, identifier):
    with pytest.raises(ValueError):
        service.load_session(identifier)


def test_progress_updates_from_distinct_instances_are_not_lost(service):
    session = service.create_session('demo')
    others = [TranslationSessionService(service.storage) for _ in range(12)]
    def write(i):
        others[i].update_progress(session.id, {f'key{i}': i})
    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(write, range(12)))
    loaded = service.load_session(session.id)
    assert loaded.progress == {f'key{i}':i for i in range(12)}


def test_failed_atomic_write_preserves_session(service, monkeypatch):
    import os
    session = service.create_session('demo')
    path = service.sessions_dir / f'{session.id}.json'
    before = path.read_bytes()
    def fail(*args):
        raise OSError('simulated full filesystem')
    monkeypatch.setattr(os, 'replace', fail)
    monkeypatch.setattr('src.core.file_utils.time.sleep', lambda _: None)
    with pytest.raises(OSError):
        service.update_progress(session.id, {'new': 1})
    assert path.read_bytes() == before
