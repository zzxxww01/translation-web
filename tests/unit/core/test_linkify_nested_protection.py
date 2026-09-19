from src.html2md.markdown import _linkify_bare_urls, SemiAnalysisMarkdownConverter


def test_social_card_keeps_images_text_and_source_without_block_link():
    html = '<a href="https://example.org/post"><img src="https://example.org/avatar.jpg"><p>Author</p><p>Post text</p><img src="https://example.org/photo.jpg"></a>'
    text = SemiAnalysisMarkdownConverter().convert(html)
    assert 'Author' in text and 'Post text' in text
    assert text.count('![') == 2
    assert '[https://example.org/post](https://example.org/post)' in text
    assert '[![' not in text
    assert '\ufff0' not in _linkify_bare_urls(text)



def test_image_inside_link_restores_nested_tokens():
    text = '[![avatar](https://example.org/avatar.jpg)\n\nname\n\n![](https://example.org/photo.jpg)](https://example.org/post)'
    result = _linkify_bare_urls(text)
    assert result == text
    assert '\ufff0' not in result


def test_link_inside_code_restores_nested_tokens():
    text = '`[name](https://example.org/post)` https://example.org/plain'
    assert _linkify_bare_urls(text) == '`[name](https://example.org/post)` [https://example.org/plain](https://example.org/plain)'
