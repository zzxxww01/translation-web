from types import SimpleNamespace
from src.agents.consistency_reviewer import ConsistencyReviewer
from src.core.models import Paragraph, Section, EnhancedTerm, TranslationStrategy, ConsistencyIssue, Glossary, GlossaryTerm
from src.core.term_consistency import check_terminology
from src.services.consistency_service import ConsistencyReviewer as LightweightReviewer, generate_consistency_report_markdown

def make_section(source):
    return Section(section_id='s1',title='Test',paragraphs=[Paragraph(id='p1',index=0,source=source)])

def test_acronym_does_not_match_word_substrings():
    terms=[EnhancedTerm(term='AI',translation='人工智能',context_meaning='AI',strategy=TranslationStrategy.TRANSLATE)]
    issues,stats=check_terminology([make_section('They said it would fail.')],{'s1':['他们说会失败。']},terms)
    assert not issues and not stats

def test_known_single_sense_mismatch_is_reported_with_correct_location():
    terms=[EnhancedTerm(term='wafer',translation='晶圆',context_meaning='fab',strategy=TranslationStrategy.TRANSLATE)]
    issues,stats=check_terminology([make_section('The wafers arrived.')],{'s1':['已经到货。']},terms)
    assert len(issues)==1 and not issues[0].auto_fixable
    assert stats['wafer']['other_hits']==1

def test_polysemy_not_forced_to_a_single_translation():
    terms=[EnhancedTerm(term='yield',translation='良率(制造)/收益率(金融)',context_meaning='多义词按语境',strategy=TranslationStrategy.TRANSLATE)]
    issues,stats=check_terminology([make_section('Bond yield rose.')],{'s1':['债券收益率上升。']},terms)
    assert not issues and stats['yield']['requires_context_review']

def test_suggestions_never_replace_entire_paragraphs():
    reviewer=ConsistencyReviewer(SimpleNamespace())
    original={'s1':['A complete paragraph.']}
    issue=ConsistencyIssue(section_id='s1',paragraph_index=0,issue_type='terminology',description='potential',auto_fixable=True,fix_suggestion='建议统一使用某词')
    fixed=reviewer.auto_fix(original,[issue])
    assert fixed==original and fixed['s1'] is not original['s1']

def test_disabled_style_checker_is_not_reported_as_perfect_score():
    section=make_section('hello');section.paragraphs[0].add_translation('你好','test')
    report=LightweightReviewer().review([section])
    assert not report.style_checked and report.reviewed_paragraphs==1
    assert '未执行' in generate_consistency_report_markdown(report)
