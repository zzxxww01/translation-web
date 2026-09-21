"""Round-trip and failure-path regressions; no external model requests."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from src.core.models import Paragraph, ParagraphStatus, Section, TranslationRecord, ProjectMeta
from src.core.project import ProjectManager
from src.core.export_completeness import build_translation_completeness


def manager_with_section(tmp_path):
    pm = ProjectManager(projects_path=str(tmp_path / 'projects'))
    section = Section(section_id='s1', title='Opening', title_translation='开篇',
                      synthetic=True, title_source='Generated intro', paragraphs=[
        Paragraph(id='p1', index=0, source='First source'),
        Paragraph(id='p2', index=1, source='Second source'),
    ])
    pm.save_section_only('demo', section)
    return pm, section, tmp_path / 'projects/demo/sections/s1/meta.json'


def test_section_round_trip_keeps_title_provenance(tmp_path):
    pm, original, _ = manager_with_section(tmp_path)
    loaded = pm.get_section('demo', 's1')
    assert loaded.synthetic is True
    assert loaded.title_source == original.title_source


@pytest.mark.parametrize('corruption', ['paragraph', 'paragraphs_type', 'duplicate_id', 'section_id', 'json'])
def test_corrupt_section_cannot_be_loaded_or_partially_overwritten(tmp_path, corruption):
    pm, _, path = manager_with_section(tmp_path)
    data = json.loads(path.read_text())
    if corruption == 'paragraph':
        data['paragraphs'][1]['index'] = 'invalid'
    elif corruption == 'paragraphs_type':
        data['paragraphs'] = None
    elif corruption == 'duplicate_id':
        data['paragraphs'][1]['id'] = 'p1'
    elif corruption == 'section_id':
        data['section_id'] = 'wrong-location'
    path.write_text('{bad' if corruption == 'json' else json.dumps(data))
    before = path.read_bytes()
    with pytest.raises(ValueError, match='[Ss]ection'):
        pm.get_sections('demo')
    with pytest.raises(ValueError, match='[Ss]ection'):
        pm.update_paragraph_locked('demo', 's1', 'p1', translation='人工译文', recompute_progress=False)
    assert path.read_bytes() == before


def test_missing_meta_in_existing_chapter_is_not_silently_omitted(tmp_path):
    pm, _, path = manager_with_section(tmp_path)
    path.unlink()
    with pytest.raises(ValueError, match='[Ss]ection'):
        pm.get_sections('demo')
    assert pm.get_section('demo', 'never-existed') is None


def test_mixed_aware_and_naive_record_dates_can_be_ordered():
    older = datetime.now() - timedelta(hours=1)
    newer = datetime.now(timezone.utc)
    paragraph = Paragraph(id='p1', index=0, source='Text', translations={
        'old': TranslationRecord(text='旧稿', model='old', created_at=older),
        'new': TranslationRecord(text='新稿', model='new', created_at=newer),
    })
    assert paragraph.best_translation_text() == '新稿'


def test_subtitle_and_source_metadata_still_need_translation():
    section = Section(section_id='s1', title='章节', paragraphs=[
        Paragraph(id='p1', index=0, source='A new generation of inference', is_metadata=True, metadata_type='subtitle'),
        Paragraph(id='p2', index=1, source='Source: Company estimates', is_metadata=True, metadata_type='source'),
        Paragraph(id='p3', index=2, source='By Jane Doe', is_metadata=True, metadata_type='byline'),
    ])
    report = build_translation_completeness([section])
    assert {i['paragraph_id'] for i in report['items']} == {'p1', 'p2'}


def test_asset_folder_symlinks_cannot_copy_server_files(tmp_path):
    pm = ProjectManager(projects_path=str(tmp_path / 'projects'))
    source = tmp_path / 'inbox/page.html'
    source.parent.mkdir()
    source.write_text('<h1>Title</h1><p>Text</p>')
    assets = source.parent / 'page_files'
    assets.mkdir()
    (assets / 'ok.png').write_bytes(b'image')
    secret = tmp_path / 'private'
    secret.mkdir()
    (secret / 'confidential.txt').write_text('must not be copied')
    (assets / 'linked').symlink_to(secret, target_is_directory=True)
    (assets / 'secret.txt').symlink_to(secret / 'confidential.txt')
    destination = tmp_path / 'projects/demo'
    destination.mkdir(parents=True)
    pm.project_lifecycle_service.copy_assets_directory(source, destination)
    assert (destination / 'page_files/ok.png').is_file()
    assert not (destination / 'page_files/linked').exists()
    assert not (destination / 'page_files/secret.txt').exists()


def test_duplicate_id_save_is_rejected_before_any_file_is_changed(tmp_path):
    pm, section, path = manager_with_section(tmp_path)
    before = {p.name: p.read_bytes() for p in path.parent.iterdir() if p.is_file()}
    section.paragraphs[1].id = section.paragraphs[0].id
    with pytest.raises(ValueError, match="identit"):
        pm.save_section_only('demo', section)
    assert {p.name: p.read_bytes() for p in path.parent.iterdir() if p.is_file()} == before
