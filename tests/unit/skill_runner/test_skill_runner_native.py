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


FAKE_CLAUDE = r'''
import json, sys
if "--version" in sys.argv:
    print("2.1.310 (Claude Code)")
elif sys.argv[1:3] == ["auth", "status"]:
    print(json.dumps({"loggedIn": True, "authMethod": "claude.ai", "subscriptionType": "pro",
                      "orgName": "Me's Organization", "email": "me@example.com"}))
'''
SESSION = {"session_id": "sess-1", "cwd": "/runs/r1", "model": "claude-opus-5-5"}


async def test_claude_status_mirrors_the_interactive_fields_and_remembers_usage(tmp_path):
    config = make_config(tmp_path, claude_bin=str(_script(tmp_path / "claude", FAKE_CLAUDE)))
    natives = Natives(config)
    lines = await natives.status_lines("claude", SESSION)
    assert lines == ["Version: 2.1.310", "Session ID: sess-1", "cwd: /runs/r1", "Login method: Claude Pro Account",
                     "Organization: Me's Organization", "Email: me@example.com", "Model: claude-opus-5-5",
                     "Usage: no data yet (appears after the first turn)"]

    reset = time.time() + 3600
    natives.observe("claude", {"type": "limits", "windows": {
        "five_hour": {"utilization": 0.28, "resetsAt": reset}, "seven_day": {"utilization": 0.43, "resetsAt": reset}}})
    natives.observe("codex", {"type": "limits", "windows": {"five_hour": {"utilization": 0.99}}})  # 别的 harness 不记
    lines = (await Natives(config).status_lines("claude"))[-3:]  # 重启后也读得到
    assert lines[0].startswith("Current session: 28% used · resets ")
    assert lines[1].startswith("Current week (all models): 43% used")
    assert lines[2].startswith("(usage as of the last turn")


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
    lines = await Natives(make_config(tmp_path, codex_bin=str(fake))).status_lines("codex", SESSION)
    assert lines == ["Version: 0.164.0", "Model: claude-opus-5-5", "Directory: /runs/r1", "Account: ChatGPT (Plan: Pro)",
                     "Session: sess-1", "5h limit: 12% used", "Weekly limit: 99% used", "Credits: 2237.89"]


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
    assert status[0] == "Version: 1.5.9" and status[-1].startswith("Gemini Models")


async def test_a_broken_cli_does_not_break_status(tmp_path):
    lines = await Natives(make_config(tmp_path, codex_bin=str(tmp_path / "missing"))).status_lines("codex")
    assert lines[0].startswith("原生信息读不到")
    assert json.dumps(lines)  # 能放进事件
