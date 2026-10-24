import json

from skill_runner.agents import build_catalog, prompt_note

from skill_runner_fakes import make_config


def install(skills_dir, name, description="desc"):
    (skills_dir / name).mkdir(parents=True)
    (skills_dir / name / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n", encoding="utf-8"
    )


def test_catalog_puts_chat_first_then_enabled_skills_with_cards(tmp_path):
    config = make_config(tmp_path)
    install(config.skills_dir, "four-step-translate")
    catalog = build_catalog(config)
    assert [a["name"] for a in catalog] == ["", "four-step-translate", "podcast-cn-dubber"]
    chat, article, podcast = catalog
    assert chat["title"] == "Claude" and chat["available"] and chat["examples"]
    assert article["title"] == "文章精翻" and article["icon"] == "article" and article["available"]
    assert article["hint"]
    # 名片有，但服务器上没装
    assert podcast["title"] == "播客配音" and not podcast["available"]


def test_skill_without_card_falls_back_to_skill_md(tmp_path):
    cards = tmp_path / "agents.json"
    cards.write_text(json.dumps([{"skill": "", "title": "聊天"}]), encoding="utf-8")
    config = make_config(tmp_path, skills=("x",), agents_file=cards)
    install(config.skills_dir, "x", "做 X 的 skill")
    chat, x = build_catalog(config)
    assert chat["title"] == "聊天" and chat["icon"] == "chat"
    assert x == {
        "name": "x", "title": "x", "icon": "skill", "description": "做 X 的 skill",
        "hint": "", "examples": [], "available": True,
    }


def test_missing_or_broken_cards_file_still_lists_chat(tmp_path):
    for content in (None, "{not json"):
        cards = tmp_path / "agents.json"
        if content is not None:
            cards.write_text(content, encoding="utf-8")
        catalog = build_catalog(make_config(tmp_path, agents_file=cards))
        assert catalog[0]["name"] == "" and catalog[0]["title"] == "Claude"


def test_chat_note_lists_installed_agents_and_skill_runs_get_none(tmp_path):
    config = make_config(tmp_path)
    install(config.skills_dir, "four-step-translate")
    catalog = build_catalog(config)
    note = prompt_note(catalog, "")
    assert "文章精翻（four-step-translate）" in note and "＋新任务" in note
    assert "podcast-cn-dubber" not in note  # 没装的不提
    assert prompt_note(catalog, "four-step-translate") == ""


async def test_runner_passes_note_to_chat_sessions_only(config, runner, factory):
    install(config.skills_dir, "four-step-translate")
    chat = runner.create("", "聊天")
    await runner.begin(chat.id, "你好", [])
    assert "文章精翻" in factory.last.spec.prompt_note

    skill = runner.create("four-step-translate", "精翻")
    await runner.begin(skill.id, "精翻这篇", [])
    assert factory.last.spec.prompt_note == ""
