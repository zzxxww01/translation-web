import io
from http.cookies import SimpleCookie

from skill_runner import auth
from src.services import agent_translate


def test_request_sends_current_and_previous_cookie_names(tmp_path, monkeypatch):
    """skill-runner 重启前只认改名前的 cookie、重启后认新的：两个都带，且都是有效签名。"""
    env_file = tmp_path / "env"
    env_file.write_text("SKILL_RUNNER_PASSWORD=s3cret\n", encoding="utf-8")
    seen = {}

    def fake_open(request, timeout):
        seen["cookie"] = request.get_header("Cookie")
        return io.BytesIO(b'{"ok": true}')

    monkeypatch.setattr(agent_translate._direct, "open", fake_open)
    client = agent_translate.SkillRunnerClient("http://127.0.0.1:18090", env_file)
    assert client.me() == {"ok": True}

    cookies = SimpleCookie(seen["cookie"])
    secret = agent_translate.read_skill_runner_secret(env_file)
    for name in (auth.COOKIE_NAME, auth.PREVIOUS_COOKIE_NAME):
        assert auth.verify_token(secret, cookies[name].value), name
