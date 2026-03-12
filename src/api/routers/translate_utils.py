"""
Translate router shared helpers.
"""

import re
from typing import Optional


def get_latest_translation_text(paragraph) -> Optional[str]:
    """Return the confirmed translation first, then the latest non-empty draft."""
    if paragraph.confirmed:
        return paragraph.confirmed
    return paragraph.latest_translation_text(non_empty=True)


def build_retranslate_instruction(
    user_instruction: str,
    source_text: str,
    current_translation: Optional[str],
) -> str:
    """Wrap short user edits with enough structure for stable retranslation."""
    instruction = user_instruction.strip()
    if not instruction:
        return ""

    if "[Source]" in instruction and "[Rules]" in instruction:
        return instruction

    parts = [f"[Revision request]\n{instruction}"]

    if source_text:
        preview = source_text[:600] + "..." if len(source_text) > 600 else source_text
        parts.append(f"[Source text]\n{preview}")

    if current_translation:
        preview = (
            current_translation[:600] + "..."
            if len(current_translation) > 600
            else current_translation
        )
        parts.append(f"[Current translation]\n{preview}")

    parts.append(
        "[Rules]\n"
        "1. The source text is ground truth: do not lose or distort facts, logic, or data.\n"
        "2. Fix errors first, then apply the revision request.\n"
        "3. Keep terminology consistent and accurate.\n"
        "4. Write natural, clear Chinese; avoid translationese.\n"
        "5. Preserve hidden format tokens exactly if present.\n"
        "6. Output only the revised translation, no explanation."
    )
    return "\n\n".join(parts)


def validate_path_component(value: str) -> bool:
    """
    Validate path component and block traversal.

    Only allow letters, numbers, underscore and hyphen.
    """
    return bool(re.match(r"^[\w\-]+$", value))
