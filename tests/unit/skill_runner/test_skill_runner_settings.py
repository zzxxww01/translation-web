"""页面自己记住的 /effort、/model，以及新对话第一句就是 CLI 查询指令的情况。"""

from skill_runner.codex_session import build_command
from skill_runner.runner import make_title

from skill_runner_fakes import make_config, settle


def reports(store, run_id):
    return [e for e in store.read_events(run_id) if e["type"] == "report"]


async def new_run(runner, first, harness="claude"):
    meta = runner.create("four-step-translate", make_title(first, []), harness=harness)
    await runner.begin(meta.id, first, [])
    return meta.id


def finish(session, sid="sess-1"):
    session.push({"type": "session", "session_id": sid})
    session.push({"type": "result", "session_id": sid, "is_error": False})


async def test_effort_first_is_remembered_and_passed_when_the_agent_starts(runner, store, factory):
    run_id = await new_run(runner, "/effort high")
    assert factory.sessions == []  # 只是设置，不起进程、不花额度
    assert runner.meta(run_id).effort == "high"
    assert "推理强度：high" in reports(store, run_id)[-1]["lines"]

    await runner.send_message(run_id, "精翻这篇", [])
    session = factory.last
    assert session.spec.effort == "high"
    assert session.sent == ["/four-step-translate 精翻这篇"]
    assert runner.meta(run_id).title == "精翻这篇"


async def test_effort_without_level_or_with_unknown_level_changes_nothing(runner, store, factory):
    run_id = await new_run(runner, "/effort")
    assert "当前推理强度：默认" in reports(store, run_id)[-1]["lines"]
    await runner.send_message(run_id, "/effort turbo", [])
    assert runner.meta(run_id).effort is None
    assert "turbo" in reports(store, run_id)[-1]["lines"][0]
    await runner.send_message(run_id, "/effort max", [])
    await runner.send_message(run_id, "/effort auto", [])
    assert runner.meta(run_id).effort is None


async def test_changing_effort_mid_conversation_restarts_the_process_on_next_message(runner, store, factory):
    run_id = await new_run(runner, "精翻这篇")
    first = factory.last
    finish(first)
    await settle()
    await runner.send_message(run_id, "/effort xhigh", [])
    assert first.closed is False  # 改设置本身不打断

    await runner.send_message(run_id, "继续", [])
    await settle()
    second = factory.last
    assert first.closed and second is not first
    assert second.spec.effort == "xhigh" and second.spec.resume == "sess-1"
    assert second.sent == ["继续"]

    finish(second)
    await settle()
    await runner.send_message(run_id, "再来一段", [])
    assert factory.last is second  # 设置没再变：不重起


async def test_effort_set_while_working_applies_after_the_turn(runner, store, factory):
    run_id = await new_run(runner, "精翻这篇")
    first = factory.last
    await runner.send_message(run_id, "/effort low", [])
    assert "这一轮做完后生效" in reports(store, run_id)[-1]["lines"][1]
    assert first.sent == ["/four-step-translate 精翻这篇"]  # 指令不发给正在干活的 agent
    finish(first)
    await settle()
    await runner.send_message(run_id, "继续", [])
    assert factory.last.spec.effort == "low"


async def test_model_command_sets_and_resets_the_model(runner, store, factory):
    run_id = await new_run(runner, "/model sonnet")
    assert runner.meta(run_id).model == "sonnet"
    await runner.send_message(run_id, "/model rm -rf", [])
    assert runner.meta(run_id).model == "sonnet"
    await runner.send_message(run_id, "开始", [])
    assert factory.last.spec.model == "sonnet"
    await runner.send_message(run_id, "/model default", [])
    assert runner.meta(run_id).model is None


async def test_codex_effort_uses_its_own_levels_and_goes_on_the_command_line(runner, store, factory, tmp_path):
    run_id = await new_run(runner, "/effort max", harness="codex")
    assert runner.meta(run_id).effort is None  # Codex 没有 max
    await runner.send_message(run_id, "/effort minimal", [])
    assert runner.meta(run_id).effort == "minimal"
    await runner.send_message(run_id, "开始", [])
    assert factory.last.spec.effort == "minimal"

    command = build_command(make_config(tmp_path, codex_model="gpt-6.1-sol"), None, effort="minimal")
    assert command[command.index("-c", command.index("-m")) + 1] == 'model_reasoning_effort="minimal"'
    assert "model_reasoning_effort" not in " ".join(build_command(make_config(tmp_path), None))


async def test_cli_info_command_first_goes_out_as_is_and_next_message_starts_the_skill(runner, store, factory):
    run_id = await new_run(runner, "/usage")
    session = factory.last
    assert session.sent == ["/usage"]
    assert runner.meta(run_id).begun is False
    finish(session)
    await settle()
    await runner.send_message(run_id, "精翻这篇", [])
    assert session.sent[-1] == "/four-step-translate 精翻这篇"
    assert runner.meta(run_id).begun is True


async def test_other_slash_text_first_still_dispatches_the_skill(runner, factory):
    await new_run(runner, "/home/zxw/a.html 帮我看看")
    assert factory.last.sent == ["/four-step-translate /home/zxw/a.html 帮我看看"]


async def test_status_card_shows_effort(runner, store, factory):
    run_id = await new_run(runner, "/effort high")
    assert runner.status_session(runner._get(run_id))["effort"] == "high"
