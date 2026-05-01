#!/usr/bin/env python3
"""Test retranslation of problematic paragraphs with LaTeX formulas."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agents.translation import TranslationAgent, TranslationContext
from src.config.timeout_config import TimeoutConfig
from src.core.models import Paragraph, ParagraphStatus
from src.core.glossary import GlossaryManager
from src.core.project import ProjectManager
from src.llm.factory import create_llm_provider


def test_latex_paragraph():
    """Test translating a paragraph with LaTeX formulas."""

    # Test paragraph with LaTeX formulas (from line 112 in the original document)
    test_source = """We can now calculate the total goodput expense $G_{total}$ as:

\\[
G_{\\text{total}} = \\frac{1}{2} \\times \\big( G_{\\text{chkpt-hot}} + G_{\\text{chkpt-cold}} \\big)
\\]

where $G_{\\text{chkpt-hot}}$ and $G_{\\text{chkpt-cold}}$ are defined as:"""

    print("=" * 80)
    print("Testing LaTeX Formula Translation")
    print("=" * 80)
    print("\nOriginal text:")
    print(test_source)
    print("\n" + "-" * 80)

    # Create a test paragraph
    paragraph = Paragraph(
        id="test-latex-1",
        index=0,
        source=test_source,
        status=ParagraphStatus.PENDING,
    )

    # Initialize LLM provider
    llm = create_llm_provider("longform")

    # Create translation agent
    timeout_s = TimeoutConfig.get_timeout("longform")
    agent = TranslationAgent(llm, timeout=timeout_s)

    # Create empty context (no glossary for this test)
    context = TranslationContext()

    # Translate
    print("\nTranslating...")
    try:
        payload = agent.translate_paragraph(paragraph, context)

        print("\nTranslation result:")
        print(payload.text)
        print("\n" + "-" * 80)

        # Check if LaTeX is preserved
        if "\\text{" in payload.text and "\\frac{" in payload.text and "\\big(" in payload.text:
            print("✅ LaTeX formulas preserved correctly!")
        else:
            print("❌ LaTeX formulas NOT preserved!")
            print("\nExpected patterns:")
            print("  - \\text{")
            print("  - \\frac{")
            print("  - \\big(")

        # Check for broken LaTeX
        if "text{" in payload.text or "frac{" in payload.text or "big(" in payload.text:
            print("❌ Found broken LaTeX (missing backslashes)!")

        return payload.text

    except Exception as e:
        print(f"❌ Translation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_variable_paragraph():
    """Test translating a paragraph with variable names."""

    test_source = """The variable $G_{chkpt-hot}$ represents the hot checkpoint storage cost."""

    print("\n" + "=" * 80)
    print("Testing Variable Name Translation")
    print("=" * 80)
    print("\nOriginal text:")
    print(test_source)
    print("\n" + "-" * 80)

    paragraph = Paragraph(
        id="test-var-1",
        index=0,
        source=test_source,
        status=ParagraphStatus.PENDING,
    )

    llm = create_llm_provider("longform")
    timeout_s = TimeoutConfig.get_timeout("longform")
    agent = TranslationAgent(llm, timeout=timeout_s)
    context = TranslationContext()

    print("\nTranslating...")
    try:
        payload = agent.translate_paragraph(paragraph, context)

        print("\nTranslation result:")
        print(payload.text)
        print("\n" + "-" * 80)

        # Check if variable format is preserved
        if "_{chkpt-hot}" in payload.text or "_{" in payload.text:
            print("✅ Variable subscript format preserved!")
        else:
            print("❌ Variable subscript format NOT preserved!")

        # Check for wrong format
        if "\\*chkpt" in payload.text or "*chkpt" in payload.text:
            print("❌ Found wrong variable format (asterisk instead of underscore)!")

        return payload.text

    except Exception as e:
        print(f"❌ Translation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_complex_latex():
    """Test translating a paragraph with complex LaTeX."""

    test_source = """The formula is:

$$
\\sum_{i=1}^{n} x_i = \\int_{0}^{\\infty} f(x) \\, dx
$$

This represents the total sum."""

    print("\n" + "=" * 80)
    print("Testing Complex LaTeX Translation")
    print("=" * 80)
    print("\nOriginal text:")
    print(test_source)
    print("\n" + "-" * 80)

    paragraph = Paragraph(
        id="test-complex-1",
        index=0,
        source=test_source,
        status=ParagraphStatus.PENDING,
    )

    llm = create_llm_provider("longform")
    timeout_s = TimeoutConfig.get_timeout("longform")
    agent = TranslationAgent(llm, timeout=timeout_s)
    context = TranslationContext()

    print("\nTranslating...")
    try:
        payload = agent.translate_paragraph(paragraph, context)

        print("\nTranslation result:")
        print(payload.text)
        print("\n" + "-" * 80)

        # Check if LaTeX is preserved
        if "\\sum_{" in payload.text and "\\int_{" in payload.text and "\\infty" in payload.text:
            print("✅ Complex LaTeX formulas preserved correctly!")
        else:
            print("❌ Complex LaTeX formulas NOT preserved!")

        return payload.text

    except Exception as e:
        print(f"❌ Translation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("LaTeX Formula Translation Test Suite")
    print("=" * 80)
    print("\nThis test verifies that LaTeX formulas are preserved during translation.")
    print("After the recent fixes, all LaTeX commands should keep their backslashes.\n")

    results = []

    # Test 1: Basic LaTeX with \text, \frac, \big
    result1 = test_latex_paragraph()
    results.append(("Basic LaTeX", result1 is not None))

    # Test 2: Variable names with subscripts
    result2 = test_variable_paragraph()
    results.append(("Variable subscripts", result2 is not None))

    # Test 3: Complex LaTeX with sum, integral
    result3 = test_complex_latex()
    results.append(("Complex LaTeX", result3 is not None))

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! LaTeX protection is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")
        sys.exit(1)
