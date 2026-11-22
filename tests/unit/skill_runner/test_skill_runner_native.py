"""/status 的原生信息：Claude 套餐用量的记录与显示、Codex app-server 查询、agy 本地指令（全用假的 CLI）。"""

import json
import sys
import time

from skill_runner.native import Natives

from skill_runner_fakes import make_config


def _script(path, body):
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(0o755)
    return path


async def test_claude_usage_is_remembered_from_the_last_turn(tmp_path):
    config = make_config(tmp_path, claude_bin=str(_script(tmp_path / "claude", "print('2.1.310 (Claude Code)')")))
    natives = Natives(config)
    assert "还没有数据" in (await natives.status_lines("claude"))[1]

    reset = time.time() + 3600
    natives.observe("claude", {"type": "limits", "windows": {
        "five_hour": {"utilization": 0.28, "resetsAt": reset}, "seven_day": {"utilization": 0.43, "resetsAt": reset}}})
    natives.observe("codex", {"type": "limits", "windows": {"five_hour": {"utilization": 0.99}}})  # 别的 harness 不记
    lines = await Natives(config).status_lines("claude")  # 重启后也读得到
    assert lines[0] == "Claude Code 2.1.310"
    assert lines[1].startswith("5 小时额度：已用 28%，") and lines[1].endswith("重置")
    assert lines[2].startswith("7 天额度：已用 43%")
    assert lines[3].startswith("（用量取自")


async def test_codex_account_and_limits_come_from_app_server(tmp_path):
    fake = _script(tmp_path / "codex", r'''
import json, sys
answers = {
    "initialize": {"userAgent": "skill-runner/0.164.0 (Ubuntu)"},
    "account/read": {"account": {"type": "chatgpt", "planType": "pro"}},
    "account/rateLimits/read": {"rateLimits": {
        "primary": {"usedPercent": 12, "windowDurationMins": 300, "resetsAt": None},
        "secondary": {"usedPercent": 99, "windowDurationMins": 10080, "resetsAt": None},
        "credits": {"hasCredits": True, "unlimited": False, "balance": "2237.8921960000"}}},
}
for line in sys.stdin:
    message = json.loads(line)
    if "id" in message:
        print(json.dumps({"id": message["id"], "result": answers[message["method"]]}), flush=True)
''')
    lines = await Natives(make_config(tmp_path, codex_bin=str(fake))).status_lines("codex")
    assert lines == ["Codex 0.164.0", "登录：ChatGPT 账号（pro）", "5 小时额度：已用 12%", "每周额度：已用 99%", "credits 余额：2237.89"]


async def test_agy_local_command_output_and_errors(tmp_path):
    response = "Gemini Models\tWeekly Limit Remaining\t99%\t2026-11-29T10:51:11Z\n"
    fake = _script(tmp_path / "agy", f'''
import json, sys
if "--version" in sys.argv:
    print("1.5.9")
elif any(a == "-p=/usage" for a in sys.argv):
    print(json.dumps({{"status": "SUCCESS", "response": {response!r}}}))
else:
    print(json.dumps({{"status": "ERROR", "response": "", "error": "unknown command"}}))
''')
    natives = Natives(make_config(tmp_path, antigravity_bin=str(fake)))
    assert natives.is_local("antigravity", " /usage ") and not natives.is_local("claude", "/usage")
    assert not natives.is_local("antigravity", "/status") and not natives.is_local("antigravity", "翻译这篇")
    [line] = await natives.agy_local(tmp_path, "/usage")
    assert line.startswith("Gemini Models Weekly Limit Remaining 99% ") and line.endswith(" 重置")
    assert await natives.agy_local(tmp_path, "/credits") == ["unknown command"]
    status = await natives.status_lines("antigravity")
    assert status[0] == "Antigravity 1.5.9" and status[1].startswith("Gemini Models")


async def test_a_broken_cli_does_not_break_status(tmp_path):
    lines = await Natives(make_config(tmp_path, codex_bin=str(tmp_path / "missing"))).status_lines("codex")
    assert lines[0].startswith("原生信息读不到")
    assert json.dumps(lines)  # 能放进事件
