from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from src.api.routers.image_cleanup import detect_image_content, ImageCleanupRequest, _cleanup_image_paragraphs_sync, _get_image_statistics_sync
from src.core.models import Paragraph, Section, ElementType

@pytest.mark.parametrize('text', ['The file chart.png shows the results.', 'read/write', 'https://example.com/article', '![figure](chart.png) Follow this explanation.', '<img src="a.png"> and text', 'A. The image/fetch/ endpoint is used here.'])
def test_prose_is_never_reclassified_as_image(text):
    assert not detect_image_content(text)

@pytest.mark.parametrize('text', ['![figure](chart.png)', '![figure](images/(v1)/chart.png)', '<img src="a.png">', 'images/chart.png', 'https://example.com/chart.jpg?size=20', '<div><img src="a.png"></div>'])
def test_standalone_images(text):
    assert detect_image_content(text)

def test_dry_run_counts_changes_but_never_writes_or_mutates():
    p=Paragraph(id='p1',index=0,source='![figure](chart.png)')
    p.add_translation('Cannot translate image','model')
    section=Section(section_id='s1',title='Test',paragraphs=[p])
    pm=Mock();pm.get_sections.return_value=[section]
    result=_cleanup_image_paragraphs_sync('demo',ImageCleanupRequest(dry_run=True),pm)
    assert result.marked_paragraphs==1 and result.cleaned_translations==1
    assert len(p.translations)==1 and p.element_type != ElementType.IMAGE
    pm.save_section_only.assert_not_called();pm.update_progress.assert_not_called()

def test_statistics_only_count_image_errors_in_images():
    p=Paragraph(id='p1',index=0,source='The error message says Cannot translate image')
    p.add_translation('错误：仅包含图片','model')
    pm=Mock();pm.get_sections.return_value=[Section(section_id='s1',title='Test',paragraphs=[p])]
    assert _get_image_statistics_sync('demo',pm).error_translations==0

@pytest.mark.parametrize('model,confirmed', [('manual',False),('llm',True)])
def test_image_cleanup_preserves_manual_or_confirmed_versions(model,confirmed):
    p=Paragraph(id='p1',index=0,source='![figure](chart.png)')
    p.add_translation('仅包含图片的界面截图',model)
    if confirmed:
        p.confirmed='仅包含图片的界面截图'
    pm=Mock();pm.get_sections.return_value=[Section(section_id='s1',title='Test',paragraphs=[p])]
    result=_cleanup_image_paragraphs_sync('demo',ImageCleanupRequest(dry_run=True),pm)
    assert result.cleaned_translations==0
    assert _get_image_statistics_sync('demo',pm).error_translations==0
