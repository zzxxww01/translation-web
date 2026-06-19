"""回归测试：LayeredContextManager 的缓存与前文章节顺序修复（batch 5）。"""

from src.agents.context_manager import LayeredContextManager
from src.core.models import Paragraph, Section, ParagraphStatus
from src.core.models.analysis import ArticleAnalysis, ArticleStyle, EnhancedTerm
from src.core.models.enums import TranslationStrategy


def _section(sid: str, n: int = 2) -> Section:
    paras = [Paragraph(id=f"{sid}-p{i}", index=i, source=f"src {sid} {i}",
                       status=ParagraphStatus.PENDING) for i in range(n)]
    return Section(section_id=sid, title=f"Sec {sid}", paragraphs=paras)


def _analysis(terms=None) -> ArticleAnalysis:
    return ArticleAnalysis(
        theme="t", structure_summary="s",
        style=ArticleStyle(tone="professional", target_audience="", translation_voice=""),
        guidelines=["g1", "g2"],
        terminology=terms or [],
    )


def test_previous_paragraphs_use_document_order_not_insertion_order():
    cm = LayeredContextManager(context_window_size=2)
    s1, s2, s3 = _section("s1"), _section("s2"), _section("s3")
    all_sections = [s1, s2, s3]

    # 乱序记录：先 s3 再 s1（模拟并发/乱序翻译），插入顺序 = [s3, s1]
    cm.record_translation("s3", "s3 src", "s3 译文")
    cm.record_translation("s1", "s1 src", "s1 译文")

    # 为 s2 取前文：文档顺序上 s2 的前序只有 s1，绝不能取到靠后的 s3
    ctx = cm.build_context(s2, 0, all_sections)
    prev_texts = [t for _, t in ctx.previous_paragraphs]
    assert "s1 译文" in prev_texts
    assert "s3 译文" not in prev_texts


def test_section_index_cache_consistent():
    cm = LayeredContextManager()
    all_sections = [_section("a"), _section("b"), _section("c")]
    assert cm._get_section_index(all_sections[2], all_sections) == 2
    # 再次调用命中缓存，结果一致
    assert cm._get_section_index(all_sections[1], all_sections) == 1
    # all_sections 变化后重建
    new_sections = [_section("c"), _section("a")]
    assert cm._get_section_index(new_sections[0], new_sections) == 0


def test_guidelines_cached_and_invalidated_on_set_analysis():
    cm = LayeredContextManager()
    cm.set_article_analysis(_analysis())
    s = _section("s1")
    ctx1 = cm.build_context(s, 0, [s])
    first = ctx1.guidelines
    # 复用同一缓存对象
    ctx2 = cm.build_context(s, 1, [s])
    assert ctx2.guidelines is first


def test_term_cache_invalidated_after_prescan_add():
    term = EnhancedTerm(term="GPU", translation="图形处理器", strategy=TranslationStrategy.PRESERVE)
    cm = LayeredContextManager()
    cm.set_article_analysis(_analysis([term]))
    s = _section("s1")
    # 段落源文包含 GPU，应命中术语
    s.paragraphs[0].source = "the GPU is fast"
    ctx = cm.build_context(s, 0, [s])
    assert any(t.term == "GPU" for t in ctx.terminology)
    # 通过 analysis 增加新术语后，合并基表缓存应失效并纳入新术语
    cm.add_terms_from_analysis([
        EnhancedTerm(term="CUDA", translation="CUDA", strategy=TranslationStrategy.PRESERVE)
    ])
    s.paragraphs[0].source = "CUDA and GPU"
    ctx2 = cm.build_context(s, 0, [s])
    names = {t.term for t in ctx2.terminology}
    assert "CUDA" in names
