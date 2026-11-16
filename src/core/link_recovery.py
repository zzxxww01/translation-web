"""Lossless link recovery: keep existing links, never invent visible labels.

Existing anchor ranges may be split while retaining their destinations and all
visible text. Unresolvable conflicts fail explicitly; no character-ratio slicing.
"""
from dataclasses import dataclass
from html import unescape
import re

from markdown_it import MarkdownIt
from markdown_it.rules_inline import link, image, autolink, html_inline
from markdown_it.rules_inline.backticks import backtick

from .format_tokens import FormatRecoveryError


@dataclass
class Span:
    start: int
    end: int
    href: str | None = None


def inspect_links(text: str) -> tuple[list[Span], set[str]]:
    # Use CommonMark's actual grammar (balanced/escaped parentheses, titles,
    # angle destinations, reference links), not a URL-truncating regex.
    md = MarkdownIt("commonmark")
    spans: list[Span] = []
    urls: set[str] = set()
    env: dict = {}
    md.parse(text, env)  # collect reference definitions

    def capture(rule):
        def wrapped(state, silent):
            start, count = state.pos, len(state.tokens)
            ok = rule(state, silent)
            if ok and not silent:
                hrefs = [t.attrGet("href") for t in state.tokens[count:] if t.type == "link_open"]
                urls.update(h for h in hrefs if h)
                spans.append(Span(start, state.pos, hrefs[0] if hrefs else None))
            return ok
        return wrapped

    for name, rule in [("link", link), ("image", image), ("autolink", autolink), ("backticks", backtick), ("html_inline", html_inline)]:
        md.inline.ruler.at(name, capture(rule))
    md.inline.parse(text, md, env, [])
    # HTML anchors must be protected as a whole, not just their tags.
    for match in re.finditer(r'<a\b[^>]*\bhref\s*=\s*([\'"])(.*?)\1[^>]*>.*?</a\s*>', text, re.I | re.S):
        urls.add(md.normalizeLink(unescape(match[2])))
        spans.append(Span(*match.span()))
    # Reference definitions are metadata, not available anchor text.
    for match in re.finditer(r'^ {0,3}\[[^\]\n]+\]:[^\n]*(?:\n|$)', text, re.M):
        spans.append(Span(*match.span()))
    return sorted(spans, key=lambda s: (s.start, -s.end)), urls


def normalized_url(href: str) -> str:
    return MarkdownIt().normalizeLink(unescape(href))


def wrap(text: str, href: str) -> str:
    md = MarkdownIt()
    href = md.normalizeLink(href)
    if not md.validateLink(href):
        raise FormatRecoveryError("链接恢复失败：不安全的链接目标")
    # Keep ordinary serialization stable; angle destinations protect parentheses.
    destination = f"<{href}>" if any(c in href for c in "() <>") else href
    return f"[{text}]({destination})"


def recover_links(text: str, elements: list) -> str:
    """Recover exact anchors first, then whole unlinked runs, or fail explicitly."""
    pending = []
    _, existing = inspect_links(text)
    seen = set(existing)
    for element in elements:
        href = normalized_url(element.href or "")
        if not href:
            raise FormatRecoveryError("链接恢复失败：原文链接缺少目标")
        if href not in seen:
            pending.append(element)
            seen.add(href)
    # Existing links, including legitimate repeated destinations, remain byte-for-byte.
    for element in list(pending):
        spans, _ = inspect_links(text)
        if not element.text:
            continue
        for match in re.finditer(re.escape(element.text), text):
            a, b = match.span()
            if not any(s.start < b and a < s.end for s in spans):
                text = text[:a] + wrap(text[a:b], element.href) + text[b:]
                pending.remove(element)
                break
    # Shared proper names can survive translation even when the whole anchor
    # does not. Split a plain existing anchor only if its old destination still
    # has meaningful text; retain its original destination/title serialization.
    for element in list(pending):
        anchors = [element.text] + re.findall(r"[A-Za-z][A-Za-z0-9.-]{2,}", element.text or "")
        recovered = False
        for anchor in dict.fromkeys(anchors):
            if not anchor:
                continue
            spans, _ = inspect_links(text)
            for match in re.finditer(re.escape(anchor), text):
                a, b = match.span()
                overlapping = [s for s in spans if s.start < b and a < s.end]
                if not overlapping:
                    text = text[:a] + wrap(text[a:b], element.href) + text[b:]
                    recovered = True
                    break
                # Only simple Markdown labels are safely divisible. Other
                # constructs remain protected and may use another free run.
                for span in overlapping:
                    raw = text[span.start:span.end]
                    label = re.match(r"\[([^\[\]\\\n]+)\](\(.*\))$", raw, re.S)
                    if not span.href or not label:
                        continue
                    lo, hi = span.start + 1, span.start + 1 + len(label[1])
                    if not (lo <= a < b <= hi):
                        continue
                    left, right = text[lo:a], text[b:hi]
                    if not any(c.isalnum() for c in left + right):
                        continue
                    suffix = label[2]
                    def old_part(part):
                        return '[' + part + ']' + suffix if any(c.isalnum() for c in part) else part
                    text = text[:span.start] + old_part(left) + wrap(text[a:b], element.href) + old_part(right) + text[span.end:]
                    recovered = True
                    break
                if recovered:
                    break
            if recovered:
                pending.remove(element)
                break
    if not pending:
        return text
    spans, _ = inspect_links(text)
    free = []
    cursor = 0
    for span in spans + [Span(len(text), len(text))]:
        if span.start > cursor:
            a, b = cursor, span.start
            while a < b and text[a].isspace():
                a += 1
            while b > a and text[b - 1].isspace():
                b -= 1
            if any(ch.isalnum() for ch in text[a:b]):
                free.append((a, b))
        cursor = max(cursor, span.end)
    # With no surviving named anchor, use meaningful unlinked runs in reading
    # order. For several missing URLs, split only at natural phrase boundaries,
    # never at arbitrary character ratios or inside an inline construct.
    if len(pending) > len(free):
        free = [(a + m.start(), a + m.end()) for a, b in free
                for m in re.finditer(r"[^，。！？；：、,;!?\n]+", text[a:b])
                if any(c.isalnum() for c in m[0])]
    free = [(a, b) for a, b in free if not any(c in text[a:b] for c in "[]<>`*_~\\")]
    if len(free) < len(pending):
        raise FormatRecoveryError(
            "链接恢复存在歧义：没有足够的合理锚文本保留全部网址；请为缺失链接指定锚文本"
        )
    if len(pending) == 1:
        free = [max(free, key=lambda pair: pair[1] - pair[0])]
    replacements = [(a, b, wrap(text[a:b], e.href)) for (a, b), e in zip(free, pending)]
    for a, b, replacement in reversed(replacements):
        text = text[:a] + replacement + text[b:]
    return text
