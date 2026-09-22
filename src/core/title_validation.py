"""Conservative language/completeness checks for Chinese title translation.

A nonempty English sentence is not a translation. Pure protected names may
remain unchanged; do not treat arbitrary Title Case headings as brand names.
This is a structural check, not a semantic translation-quality score.
"""
import re

_HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U0002fa1f]")
# Names without distinctive spelling cannot safely be inferred from capitalization.
_NAMES = {
    "openai", "anthropic", "nvidia", "amd", "intel", "google", "google cloud",
    "microsoft", "microsoft azure", "amazon", "amazon web services", "apple",
    "meta", "tesla", "cerebras", "samsung", "tsmc", "qualcomm", "broadcom",
    "deepseek", "chatgpt", "github", "hugging face", "semi analysis", "semianalysis",
    "claude", "gemini", "copilot", "bedrock", "azure", "aws", "arm", "rocm", "sglang",
    "tokenomics", "token", "qwen", "kimi", "minimax",
    # Robotics startups have no established Chinese names; headings keep the
    # English company name (user-confirmed for the on-device vs datacenter piece).
    "agility robotics", "verne robotics", "sunday robotics", "weave robotics",
}
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9._+-]*")


def is_protected_name(text: str) -> bool:
    """Shared standalone-name policy for title validation and export coverage."""
    if text.casefold() in _NAMES:
        return True
    # Model-only labels may include spaces and versions, but not prose such as
    # "Trillion Parameters" or "is catching up".
    if re.fullmatch(r"(?:DeepSeek|Qwen|Kimi|MiniMax|GLM|GPT|Claude|Gemini)(?:[ -]?[VMK]?\d[\d.Xx-]*)?(?: (?:[VMK]?\d[\d.Xx-]*[BT]?|Pro|Flash|Preview|Turbo|FP\d+))*", text):
        return True
    if not _IDENTIFIER.fullmatch(text):
        return False
    return bool(
        re.search(r"[a-z][A-Z]", text)  # OpenAI, CoreWeave, vLLM
        or re.fullmatch(r"[A-Z]{2,}[0-9.-]*", text)  # CUDA, AI, H100
        or re.search(r"[A-Za-z].*\d", text)  # GPT-5, N2
    )


def is_valid_title_translation(source: str, translated: object) -> bool:
    """Require Chinese text, or an exact unchanged protected-only source."""
    if not isinstance(translated, str) or not translated.strip():
        return False
    source, translated = (source or "").strip(), translated.strip()
    if _HAN.search(translated):
        return True
    if translated != source:
        return False
    if not re.search(r"[A-Za-z]", source):
        return any(char.isdigit() for char in source)
    return is_protected_name(source)
