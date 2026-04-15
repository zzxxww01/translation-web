#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated verification script for Slack conversation context implementation.
Checks that all required components are in place before manual E2E testing.
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_backend_models():
    """Verify backend data models are correctly defined."""
    print("✓ Checking backend models...")

    from src.api.routers.slack_models import (
        ConversationMessage,
        SlackProcessRequest,
        SlackComposeRequest,
    )

    # Check ConversationMessage has required fields
    msg = ConversationMessage(role="me", content="test")
    assert msg.role == "me"
    assert msg.content == "test"

    # Check SlackProcessRequest has conversation_history
    req = SlackProcessRequest(message="test")
    assert hasattr(req, "conversation_history")
    assert req.conversation_history == []

    # Check SlackComposeRequest has conversation_history
    req2 = SlackComposeRequest(content="test")
    assert hasattr(req2, "conversation_history")
    assert req2.conversation_history == []

    print("  ✓ ConversationMessage model defined")
    print("  ✓ SlackProcessRequest has conversation_history field")
    print("  ✓ SlackComposeRequest has conversation_history field")


def check_backend_formatting():
    """Verify conversation history formatting function exists."""
    print("\n✓ Checking backend formatting functions...")

    from src.api.routers.slack_process import format_conversation_history
    from src.api.routers.slack_models import ConversationMessage

    # Test empty history
    result = format_conversation_history([])
    assert result == ""

    # Test with messages
    messages = [
        ConversationMessage(role="them", content="Hello"),
        ConversationMessage(role="me", content="Hi there"),
    ]
    result = format_conversation_history(messages)
    assert "## Conversation history" in result
    assert "[Them]: Hello" in result
    assert "[Me]: Hi there" in result

    print("  ✓ format_conversation_history function exists")
    print("  ✓ Empty history returns empty string")
    print("  ✓ Messages formatted correctly")


def check_prompt_templates():
    """Verify prompt templates have conversation_history_section placeholder."""
    print("\n✓ Checking prompt templates...")

    slack_process_path = project_root / "src" / "prompts" / "slack_process.txt"
    slack_compose_path = project_root / "src" / "prompts" / "slack_compose.txt"

    # Check slack_process.txt
    with open(slack_process_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "{conversation_history_section}" in content, \
            "slack_process.txt missing {conversation_history_section} placeholder"
        assert "Consider the conversation history" in content, \
            "slack_process.txt missing instruction to consider history"

    print("  ✓ slack_process.txt has {conversation_history_section}")
    print("  ✓ slack_process.txt has history instruction")

    # Check slack_compose.txt
    with open(slack_compose_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "{conversation_history_section}" in content, \
            "slack_compose.txt missing {conversation_history_section} placeholder"
        assert "Consider the conversation history" in content, \
            "slack_compose.txt missing instruction to consider history"

    print("  ✓ slack_compose.txt has {conversation_history_section}")
    print("  ✓ slack_compose.txt has history instruction")


def check_api_integration():
    """Verify API endpoints use conversation history."""
    print("\n✓ Checking API integration...")

    from src.api.routers.slack_process import format_conversation_history

    # Check that format_conversation_history is imported/used
    slack_process_path = project_root / "src" / "api" / "routers" / "slack_process.py"
    with open(slack_process_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "format_conversation_history" in content
        assert "request.conversation_history" in content
        assert "conversation_history_section" in content

    print("  ✓ slack_process.py uses format_conversation_history")
    print("  ✓ slack_process.py passes conversation_history to prompt")

    slack_compose_path = project_root / "src" / "api" / "routers" / "slack_compose.py"
    with open(slack_compose_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "format_conversation_history" in content
        assert "request.conversation_history" in content
        assert "conversation_history_section" in content

    print("  ✓ slack_compose.py uses format_conversation_history")
    print("  ✓ slack_compose.py passes conversation_history to prompt")


def check_frontend_types():
    """Verify frontend types are defined."""
    print("\n✓ Checking frontend types...")

    types_path = project_root / "web" / "frontend" / "src" / "shared" / "types" / "index.ts"
    with open(types_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "ConversationMessage" in content
        assert "MessageRole" in content or "'them' | 'me'" in content
        assert "conversation_history" in content.lower()

    print("  ✓ ConversationMessage type defined")
    print("  ✓ MessageRole type defined")
    print("  ✓ API DTOs include conversation_history")


def check_frontend_store():
    """Verify frontend store has conversation management."""
    print("\n✓ Checking frontend store...")

    store_path = project_root / "web" / "frontend" / "src" / "features" / "slack" / "store.ts"
    with open(store_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "conversationMessages" in content
        assert "isHistoryCollapsed" in content
        assert "addMessage" in content
        assert "addMessages" in content
        assert "removeMessage" in content
        assert "updateMessage" in content
        assert "clearConversation" in content
        assert "toggleHistoryCollapse" in content

    print("  ✓ conversationMessages state exists")
    print("  ✓ isHistoryCollapsed state exists")
    print("  ✓ addMessage action exists")
    print("  ✓ addMessages action exists")
    print("  ✓ removeMessage action exists")
    print("  ✓ updateMessage action exists")
    print("  ✓ clearConversation action exists")
    print("  ✓ toggleHistoryCollapse action exists")


def check_frontend_component():
    """Verify ConversationHistory component exists."""
    print("\n✓ Checking frontend component...")

    component_path = project_root / "web" / "frontend" / "src" / "features" / "slack" / "components" / "ConversationHistory.tsx"
    assert component_path.exists(), "ConversationHistory.tsx not found"

    with open(component_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "ConversationHistory" in content
        assert "messages" in content
        assert "isCollapsed" in content
        assert "onToggleCollapse" in content
        assert "onRemoveMessage" in content
        assert "onUpdateMessage" in content
        assert "onClearAll" in content

    print("  ✓ ConversationHistory component exists")
    print("  ✓ Component has all required props")


def check_frontend_integration():
    """Verify main UI integrates conversation history."""
    print("\n✓ Checking frontend integration...")

    index_path = project_root / "web" / "frontend" / "src" / "features" / "slack" / "index.tsx"
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "ConversationHistory" in content
        assert "conversationMessages" in content
        assert "conversation_history" in content
        assert "addMessage" in content or "addMessages" in content

    print("  ✓ ConversationHistory component imported")
    print("  ✓ conversationMessages used in component")
    print("  ✓ conversation_history passed to API calls")
    print("  ✓ Messages added to history on user actions")


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Slack Conversation Context Implementation Verification")
    print("=" * 60)

    try:
        check_backend_models()
        check_backend_formatting()
        check_prompt_templates()
        check_api_integration()
        check_frontend_types()
        check_frontend_store()
        check_frontend_component()
        check_frontend_integration()

        print("\n" + "=" * 60)
        print("✅ ALL CHECKS PASSED")
        print("=" * 60)
        print("\nImplementation is complete and ready for E2E testing.")
        print("\nNext steps:")
        print("1. Start backend: python -m uvicorn src.api.app:app --reload --port 54321")
        print("2. Start frontend: cd web/frontend && npm run dev")
        print("3. Follow test plan: docs/superpowers/test-plans/2026-04-15-slack-context-e2e-test.md")

        return 0

    except AssertionError as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
