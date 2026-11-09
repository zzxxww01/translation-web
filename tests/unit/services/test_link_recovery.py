from types import SimpleNamespace
import re
import pytest
from markdown_it import MarkdownIt
from src.core.link_recovery import recover_links, inspect_links
from src.core.format_tokens import FormatRecoveryError


def element(text, href):
    return SimpleNamespace(text=text, href=href)


def visible(text):
    return ''.join(t.content for b in MarkdownIt().parse(text) for t in (b.children or []) if t.type in {'text', 'code_inline'})


@pytest.mark.parametrize('text,links', [
    ('[Meta 与 SemiAnalysis 估算](https://semi.test "title")', [element('Meta','https://meta.test')]),
    ('来源：Meta，SemiAnalysis 估算', [element('Meta','https://meta.test'), element('SemiAnalysis Estimates','https://semi.test')]),
    ('[Meta、Google 与 SemiAnalysis](https://semi.test)', [element('Meta','https://meta.test'),element('Google','https://google.test')]),
    ('前文说明，[季度报告分析](https://b.test)，其余内容。', [element('quarterly report','https://a.test')]),
    ('甲公司，乙公司。', [element('Alpha','https://a.test'),element('Beta','https://b.test')]),
])
def test_lossless_recovery(text, links):
    out = recover_links(text, links)
    assert visible(out) == visible(text)
    assert inspect_links(out)[1] >= inspect_links(text)[1] | {e.href for e in links}
    assert not re.search(r'\[[^\]\[]*\[[^\]]*\]\(',out)
    assert recover_links(out, links) == out


@pytest.mark.parametrize('text,href', [
    ('[甲](https://x.test/a_(b) "title") 与 [乙](https://x.test/a_(b))','https://x.test/a_(b)'),
    ('[甲](<https://x.test/a)b> "title")','https://x.test/a)b'),
    (r'[甲](https://x.test/a_\(b\))','https://x.test/a_(b)'),
    ('[甲][ref]\n\n[ref]: https://x.test/ref "title"','https://x.test/ref'),
    ('<a href="https://x.test/a">甲</a>','https://x.test/a'),
])
def test_existing_links_unchanged(text,href):
    assert recover_links(text,[element('甲',href),element('甲',href)]) == text


def test_complex_new_destination():
    out = recover_links('甲公司',[element('甲公司','https://x.test/a)b')])
    assert inspect_links(out)[1] == {'https://x.test/a)b'}


def test_impossible_fails_explicitly():
    with pytest.raises(FormatRecoveryError):
        recover_links('[甲](https://old.test)',[element('甲','https://new.test')])
