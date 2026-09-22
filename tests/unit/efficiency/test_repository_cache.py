import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from src.core.project_repository import ProjectRepository, SectionDataError
from src.core.file_utils import write_json_atomic
from src.core.models import Paragraph, Section


def repository(tmp_path):
    path=tmp_path/'demo'/'sections'/'s1'/'meta.json'
    section=Section(section_id='s1',title='Title',paragraphs=[Paragraph(id='p1',index=0,source='Source')])
    path.parent.mkdir(parents=True)
    write_json_atomic(path,section.model_dump(mode='json'))
    reader=Mock(side_effect=lambda p:json.loads(p.read_text()))
    repo=ProjectRepository(project_dir_resolver=lambda p:tmp_path/p, read_json=reader,
        write_json=write_json_atomic,write_text=lambda *a:None,get_project=lambda *a:None,
        render_source_block_markdown=lambda *a:'', render_markdown_line=lambda *a:'', best_translation_text=lambda *a:'')
    return repo,reader,path


def test_unchanged_chapter_loaded_once_and_returns_independent_objects(tmp_path):
    repo,read,path=repository(tmp_path)
    first=repo.load_section('demo','s1')
    first.paragraphs[0].source='mutated caller'
    assert repo.load_section('demo','s1').paragraphs[0].source=='Source'
    assert read.call_count==1


def test_atomic_manual_update_invalidates_cache_and_preserves_confirmed_text(tmp_path):
    repo,read,path=repository(tmp_path)
    first=repo.load_section('demo','s1')
    first.paragraphs[0].confirm('人工修改')
    write_json_atomic(path,first.model_dump(mode='json'))
    assert repo.load_section('demo','s1').paragraphs[0].confirmed=='人工修改'
    assert read.call_count==2


def test_corruption_not_masked_by_last_valid_cache(tmp_path):
    repo,read,path=repository(tmp_path)
    repo.load_section('demo','s1')
    path.write_text('{broken')
    with pytest.raises(SectionDataError): repo.load_section('demo','s1')
    path.unlink()
    with pytest.raises(SectionDataError): repo.load_section('demo','s1')


def test_same_size_in_place_source_update_invalidates(tmp_path):
    repo,read,path=repository(tmp_path)
    repo.load_section('demo','s1')
    raw=path.read_text().replace('Source','Change')
    path.write_text(raw)
    assert repo.load_section('demo','s1').paragraphs[0].source=='Change'
    assert read.call_count==2
