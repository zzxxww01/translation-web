"""Local response contracts. JSON validity is not a semantic quality guarantee."""
from __future__ import annotations
import hashlib
import json
import math
import re
from collections import Counter
from typing import Any

class PromptContractError(ValueError):
    pass

def parse_json(response: str) -> Any:
    if not isinstance(response, str) or not response.strip():
        raise PromptContractError("Empty model response")
    text = response.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
    # Duplicate object keys can hide duplicate paragraph IDs; never silently overwrite.
    def unique_pairs(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise PromptContractError(f"Duplicate JSON key: {key}")
            obj[key] = value
        return obj
    def invalid_constant(value):
        raise PromptContractError(f"Non-finite JSON number: {value}")
    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise PromptContractError("Non-finite JSON number")
        return parsed
    decoder = json.JSONDecoder(object_pairs_hook=unique_pairs, parse_constant=invalid_constant, parse_float=finite_float)
    try:
        return decoder.decode(text)
    except json.JSONDecodeError:
        # Permit a complete top-level object/array surrounded by prose, not repaired fragments.
        start = re.search(r"[\[{]", text)
        if start:
            try:
                obj, end = decoder.raw_decode(text, start.start())
                if not re.search(r"[\[{]", text[end:]):
                    return obj
            except json.JSONDecodeError:
                pass
        raise PromptContractError("Response does not contain a complete JSON value") from None

def object_response(response: str, required: tuple[str, ...] = ()) -> dict:
    result = parse_json(response)
    if not isinstance(result, dict) or any(key not in result for key in required):
        raise PromptContractError(f"Expected object with fields {required}")
    return result

def translation_items(value: Any, expected_ids: list[str]) -> list[dict[str, str]]:
    """Reject duplicates/unknown IDs; allow missing IDs for explicit per-ID fallback."""
    raw = value.get("translations") if isinstance(value, dict) else value
    if not isinstance(raw, list):
        raise PromptContractError("translations must be an array")
    expected = set(expected_ids)
    if len(expected) != len(expected_ids):
        raise PromptContractError("Input paragraph IDs must be unique")
    seen, items = set(), []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise PromptContractError("Every translation must have a string ID")
        key = item["id"]
        if key not in expected or key in seen:
            raise PromptContractError(f"Duplicate or unknown translation ID: {key}")
        seen.add(key)
        text = item.get("translation")
        if not isinstance(text, str):
            raise PromptContractError(f"Invalid translation for {key}")
        if text.strip():
            items.append({"id": key, "translation": text})
    by_id = {item["id"]: item for item in items}
    return [by_id[key] for key in expected_ids if key in by_id]

def validate_review(value: Any, sources: list[str], translations: list[str]) -> dict:
    if len(sources) != len(translations):
        raise PromptContractError("Review source/translation counts differ")
    if not isinstance(value, dict) or not isinstance(value.get("issues"), list):
        raise PromptContractError("Review must contain an explicit issues array")
    if value.get("review_status", "complete") != "complete":
        raise PromptContractError("Reviewer did not complete the review")
    coverage = value.get("coverage", 1.0)
    if isinstance(coverage, bool) or not isinstance(coverage, (int, float)) or coverage != 1.0:
        raise PromptContractError("Review coverage is incomplete")
    clean = dict(value)
    issues = []
    severities = {"critical": "P0", "high": "P1", "medium": "P2", "low": "P2"}
    for issue in value["issues"]:
        if not isinstance(issue, dict):
            raise PromptContractError("Invalid review issue")
        idx = issue.get("paragraph_index")
        severity = issue.get("severity")
        if type(idx) is not int or not 0 <= idx < len(sources) or severity not in severities:
            raise PromptContractError("Invalid review location or severity")
        if not isinstance(issue.get("description"), str) or not issue["description"].strip():
            raise PromptContractError("Review issue requires a description")
        if not isinstance(issue.get("original_text"), str) or not issue["original_text"].strip():
            raise PromptContractError("Review issue requires source evidence")
        kind = issue.get("issue_type", "readability")
        if kind not in {"accuracy", "terminology", "tone", "readability", "structure", "formatting", "data", "annotation", "style", "logic", "consistency", "fluency", "completeness"}:
            raise PromptContractError("Unknown review issue type")
        for field in ("suggestion", "why_it_matters"):
            if field in issue and not isinstance(issue[field], str):
                raise PromptContractError(f"Invalid review {field}")
        entry = dict(issue, issue_type=kind, priority=severities[severity])
        # Supplied evidence must be literal evidence; an omission may have no translated span.
        for field, source in (("original_text", sources[idx]), ("translation_text", translations[idx])):
            quote = entry.get(field, "")
            if not isinstance(quote, str):
                raise PromptContractError(f"Invalid {field}")
            if quote and quote not in source:
                raise PromptContractError(f"Unverifiable review evidence at paragraph {idx}: {field}")
        issues.append(entry)
    clean["issues"] = issues
    for key, value in list(clean.items()):
        if key.endswith("_score"):
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value <= 10:
                raise PromptContractError(f"Invalid diagnostic score {key}")
    counts = Counter(issue["severity"] for issue in issues)
    for severity in severities:
        clean[f"{severity}_issues_count"] = counts[severity]
    clean["is_excellent"] = not issues
    return clean

def text_version(sources: list[str], translations: list[str]) -> str:
    return hashlib.sha256(json.dumps([sources, translations], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()

def parse_title_lines(response: str) -> dict[str, str]:
    """Strip only a matched prefix; preserve any colon inside a title."""
    if not isinstance(response, str) or not response.strip():
        raise PromptContractError("Empty title response")
    result = {}
    for line in response.strip().splitlines():
        match = re.match(r"^(副标题|标题)\s*[:：]\s*(.*)$", line.strip())
        if match:
            key = "subtitle" if match[1] == "副标题" else "title"
            text = match[2].strip()
            if text not in ("", "无", "(无)", "（无）", "N/A"):
                result[key] = text
    if not result.get("title"):
        first = response.strip().splitlines()[0].strip()
        if first.startswith("副标题"):
            raise PromptContractError("Missing title")
        result["title"] = first
    return result


def review_regressed(before, after) -> bool:
    """Reject new/escalated serious findings, not merely a higher total count.

    Anchor matching is deliberately conservative: an unchanged count can hide a
    fixed problem in one source span and a newly introduced problem elsewhere.
    """
    if after.review_status != "complete" or after.coverage != 1.0:
        return True
    rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    old = [i for i in before.issues if i.severity in {"high", "critical"}]
    for issue in after.issues:
        if issue.severity not in {"high", "critical"}:
            continue
        def same_anchor(previous):
            a, b = previous.original_text.strip(), issue.original_text.strip()
            return (previous.paragraph_index == issue.paragraph_index
                    and previous.issue_type == issue.issue_type
                    and bool(a and b) and (a in b or b in a))
        matching = [previous for previous in old if same_anchor(previous)]
        if not matching or rank[issue.severity] > max(rank[previous.severity] for previous in matching):
            return True
        # One old finding cannot justify arbitrarily many new serious findings.
        old.remove(max(matching, key=lambda previous: rank[previous.severity]))
    return False
