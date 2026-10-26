"""Runtime maintenance uses fake installers; these tests never upgrade this machine."""

import asyncio
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


class MaintenanceRunner:
    def __init__(self):
        self.reserved = False
        self.busy = False
        self.closed = False

    def reserve_runtime_update(self):
        if self.busy or self.reserved:
            raise RuntimeError("busy")
        self.reserved = True

    async def close_idle_for_runtime_update(self):
        assert self.reserved
        self.closed = True

    def release_runtime_update(self):
        self.reserved = False


def setup_service(monkeypatch, config, tmp_path):
    module = importlib.import_module("skill_runner.runtime_updates")
    calls = []
    versions = {"claude": "2.1.300", "codex": "0.163.0"}
    prefix = tmp_path / "npm"
    root = prefix / "lib" / "node_modules"
    script = root / "@openai" / "codex" / "bin" / "codex.js"
    script.parent.mkdir(parents=True)
    script.touch()
    (prefix / "bin").mkdir()
    monkeypatch.setattr(module, "claude_cli_path", lambda config: "claude")
    monkeypatch.setattr(module.shutil, "which", lambda name: str(script) if name == "codex" else name)
    monkeypatch.setattr(module, "_latest_version", lambda harness: {"claude": "2.1.310", "codex": "0.164.0"}[harness])

    async def command(argv, timeout=15):
        calls.append(argv)
        if argv[-1] == "--version":
            harness = "claude" if argv[0] == "claude" else "codex"
            return versions[harness]
        if argv[1:] == ["prefix", "--global"]:
            return str(prefix)
        if argv[1:] == ["root", "--global"]:
            return str(root)
        if argv[1] == "install":
            harness = "claude" if argv[0] == "claude" else "codex"
            versions[harness] = "2.1.310" if harness == "claude" else "0.164.0"
            return "installed"
        raise AssertionError(argv)

    monkeypatch.setattr(module, "_command", command)
    runner = MaintenanceRunner()
    service = module.RuntimeUpdates(config, runner)
    return module, service, runner, calls, versions


async def finish(service):
    await service._task
    return service.snapshot()


def item(snapshot, harness):
    return next(runtime for runtime in snapshot["runtimes"] if runtime["harness"] == harness)


async def test_antigravity_version_check_does_not_run_installer(monkeypatch, config, tmp_path):
    module, service, _, calls, _ = setup_service(monkeypatch, config, tmp_path)
    monkeypatch.setattr(module, "_latest_version", lambda harness: "1.4.8")

    async def command(argv, timeout=15):
        calls.append(argv)
        assert argv[-1] == "--version"
        return "agy version 1.4.7"

    monkeypatch.setattr(module, "_command", command)
    await service._check_one("antigravity")
    runtime = item(service.snapshot(), "antigravity")
    assert (runtime["current"], runtime["latest"]) == ("1.4.7", "1.4.8")
    assert runtime["update_available"] and not runtime["can_update"]
    assert "自动更新" in runtime["reason"]
    with pytest.raises(ValueError, match="自动更新"):
        await service.start("antigravity")
    assert len(calls) == 1


def test_antigravity_manifest_is_selected_for_fixed_supported_platform(monkeypatch):
    module = importlib.import_module("skill_runner.runtime_updates")
    urls = []
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            return b'{"version":"1.4.7"}'
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(module.platform, "libc_ver", lambda: ("glibc", "2.35"))
    monkeypatch.setattr(module, "urlopen", lambda url, timeout: urls.append(url) or Response())
    assert module._latest_version("antigravity") == "1.4.7"
    assert urls == [module.ANTIGRAVITY_RELEASES + "/manifests/linux_amd64.json"]
    monkeypatch.setattr(module.platform, "machine", lambda: "unknown/../../bad")
    with pytest.raises(ValueError):
        module._latest_version("antigravity")


async def test_check_reports_installed_and_registry_versions_without_installing(monkeypatch, config, tmp_path):
    _, service, _, calls, _ = setup_service(monkeypatch, config, tmp_path)
    result = await service.check()
    codex = item(result, "codex")
    assert (codex["current"], codex["latest"]) == ("0.163.0", "0.164.0")
    assert codex["can_update"] and codex["update_available"]
    assert result["checked_at"] and not result["active"]
    assert all("install" not in call for call in calls)


@pytest.mark.parametrize("harness", ["claude", "codex"])
async def test_update_closes_idle_sessions_and_verifies_actual_runtime(monkeypatch, config, tmp_path, harness):
    _, service, runner, calls, _ = setup_service(monkeypatch, config, tmp_path)
    await service.check()
    result = await service.start(harness)
    assert result["active"] and runner.reserved
    result = await finish(service)
    assert runner.closed and not runner.reserved and not service.active
    assert item(result, harness)["status"] == "succeeded"
    assert not item(result, harness)["update_available"]
    install = next(call for call in calls if "install" in call)
    if harness == "codex":
        assert "@openai/codex@0.164.0" in install
        assert "--registry=https://registry.npmjs.org" in install
    else:
        assert install == ["claude", "install", "2.1.310"]


async def test_rejects_duplicate_and_busy_updates_before_installer(monkeypatch, config, tmp_path):
    _, service, runner, calls, _ = setup_service(monkeypatch, config, tmp_path)
    await service.check()
    runner.busy = True
    with pytest.raises(RuntimeError, match="busy"):
        await service.start("claude")
    assert not service.active
    runner.busy = False
    await service.start("claude")
    with pytest.raises(Exception, match="更新|busy"):
        await service.start("codex")
    await finish(service)
    assert sum("install" in call for call in calls) == 1


@pytest.mark.parametrize("harness", ["bash", "codex;echo bad", "", "CLAUDE"])
async def test_request_cannot_select_arbitrary_command(monkeypatch, config, tmp_path, harness):
    _, service, _, calls, _ = setup_service(monkeypatch, config, tmp_path)
    with pytest.raises(ValueError):
        await service.start(harness)
    assert not calls


async def test_rejects_update_before_check_and_registry_command_injection(monkeypatch, config, tmp_path):
    module, service, _, calls, _ = setup_service(monkeypatch, config, tmp_path)
    with pytest.raises(ValueError, match="检查"):
        await service.start("codex")
    monkeypatch.setattr(module, "_latest_version", lambda harness: "0.164.0;echo bad")
    result = await service.check()
    assert item(result, "codex")["error"]
    with pytest.raises(ValueError):
        await service.start("codex")
    assert all("install" not in call for call in calls)


async def test_registry_failure_does_not_claim_runtime_is_current(monkeypatch, config, tmp_path):
    module, service, _, _, _ = setup_service(monkeypatch, config, tmp_path)
    def fail(harness):
        raise TimeoutError("registry timeout")
    monkeypatch.setattr(module, "_latest_version", fail)
    result = await service.check()
    assert item(result, "claude")["latest"] is None
    assert "timeout" in item(result, "claude")["error"]
    assert not item(result, "claude")["can_update"]


async def test_unsupported_codex_installation_is_read_only(monkeypatch, config, tmp_path):
    module, service, _, calls, _ = setup_service(monkeypatch, config, tmp_path)
    monkeypatch.setattr(module.shutil, "which", lambda name: str(tmp_path / name))
    result = await service.check()
    assert not item(result, "codex")["can_update"]
    assert "npm" in item(result, "codex")["reason"]
    with pytest.raises(ValueError):
        await service.start("codex")
    assert all("install" not in call for call in calls)


async def test_version_mismatch_fails_and_releases_maintenance(monkeypatch, config, tmp_path):
    module, service, runner, _, _ = setup_service(monkeypatch, config, tmp_path)
    await service.check()
    original = module._command
    async def no_upgrade(argv, timeout=15):
        return "done" if "install" in argv else await original(argv, timeout)
    monkeypatch.setattr(module, "_command", no_upgrade)
    await service.start("claude")
    result = await finish(service)
    assert item(result, "claude")["status"] == "failed"
    assert "2.1.310" in item(result, "claude")["error"]
    assert not runner.reserved


async def test_failed_or_cancelled_installer_releases_maintenance(monkeypatch, config, tmp_path):
    module, service, runner, _, _ = setup_service(monkeypatch, config, tmp_path)
    await service.check()
    async def blocked(argv, timeout=15):
        raise TimeoutError("installer timeout")
    monkeypatch.setattr(module, "_command", blocked)
    await service.start("claude")
    result = await finish(service)
    assert "timeout" in item(result, "claude")["error"]
    assert not runner.reserved
    await service.check()
    # Check failure clears update eligibility; retry requires another successful check.
    with pytest.raises(ValueError):
        await service.start("claude")


async def test_shutdown_cancels_worker_before_releasing_gate(monkeypatch, config, tmp_path):
    module, service, runner, _, _ = setup_service(monkeypatch, config, tmp_path)
    await service.check()
    started = asyncio.Event()
    cancelled = asyncio.Event()
    async def blocked(argv, timeout=15):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
    monkeypatch.setattr(module, "_command", blocked)
    await service.start("claude")
    await started.wait()
    await service.shutdown()
    assert cancelled.is_set() and not runner.reserved
    assert item(service.snapshot(), "claude")["status"] == "failed"


def test_claude_path_prefers_explicit_native_then_path(monkeypatch, tmp_path):
    paths = importlib.import_module("skill_runner.runtime_paths")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(paths.shutil, "which", lambda command: "/path/claude")
    native = tmp_path / ".local" / "bin" / ("claude.exe" if paths.os.name == "nt" else "claude")
    native.parent.mkdir(parents=True)
    native.touch()
    monkeypatch.setattr(paths.os, "access", lambda *args: True)
    assert paths.claude_cli_path(SimpleNamespace(claude_bin="/explicit/claude")) == str(Path("/explicit/claude"))
    assert paths.claude_cli_path(SimpleNamespace(claude_bin=None)) == str(native)
    native.unlink()
    assert paths.claude_cli_path(SimpleNamespace(claude_bin=None)) == "/path/claude"


def test_registry_download_is_fixed_https_and_validates_version(monkeypatch):
    module = importlib.import_module("skill_runner.runtime_updates")
    urls = []
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            return json.dumps({"version": "0.164.0"}).encode()
    def open_url(url, timeout):
        urls.append(url)
        assert timeout <= 15
        return Response()
    monkeypatch.setattr(module, "urlopen", open_url)
    assert module._latest_version("codex") == "0.164.0"
    assert urls == ["https://registry.npmjs.org/@openai%2fcodex/latest"]
    with pytest.raises((KeyError, ValueError)):
        module._latest_version("https://evil.test")


async def test_command_timeout_kills_and_waits_for_child(monkeypatch):
    module = importlib.import_module("skill_runner.runtime_updates")
    process = SimpleNamespace(pid=98765, returncode=None)
    killed = []
    async def wait():
        if killed:
            process.returncode = -9
            return -9
        await asyncio.Event().wait()
    process.wait = wait
    process.kill = lambda: killed.append(True)
    async def create(*argv, **kwargs):
        assert kwargs.get("shell") is not True
        return process
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", create)
    monkeypatch.setattr(module.os, "killpg", lambda *args: killed.append(True), raising=False)
    with pytest.raises((TimeoutError, RuntimeError), match="超时|timeout"):
        await module._command(["fake", "--version"], timeout=0.001)
    assert killed and process.returncode == -9


async def test_check_and_start_cannot_overlap(monkeypatch, config, tmp_path):
    module, service, _, _, _ = setup_service(monkeypatch, config, tmp_path)
    await service.check()
    started = asyncio.Event()
    release = asyncio.Event()
    original = module._command
    async def blocked(argv, timeout=15):
        started.set()
        await release.wait()
        return await original(argv, timeout)
    monkeypatch.setattr(module, "_command", blocked)
    task = asyncio.create_task(service.check())
    await started.wait()
    with pytest.raises(Exception, match="检查"):
        await service.start("claude")
    with pytest.raises(Exception, match="检查"):
        await service.check()
    release.set()
    await task


async def test_shutdown_before_worker_starts_releases_reservation(monkeypatch, config, tmp_path):
    _, service, runner, calls, _ = setup_service(monkeypatch, config, tmp_path)
    await service.check()
    await service.start("claude")
    await service.shutdown()
    assert not runner.reserved and not service.active
    assert item(service.snapshot(), "claude")["status"] == "failed"
    assert all("install" not in call for call in calls)


async def test_permission_failure_and_custom_cli_are_actionable(monkeypatch, config, tmp_path):
    module, service, _, calls, _ = setup_service(monkeypatch, config, tmp_path)
    monkeypatch.setattr(module.os, "access", lambda *args: False)
    result = await service.check()
    assert "权限" in item(result, "codex")["reason"]
    service.config = SimpleNamespace(codex_bin="codex", claude_bin="/custom/claude")
    result = await service.check()
    assert "SKILL_RUNNER_CLAUDE_BIN" in item(result, "claude")["reason"]
    assert not item(result, "claude")["can_update"]
    assert all("install" not in call for call in calls)


async def test_codex_binary_directory_requires_write_permission(monkeypatch, config, tmp_path):
    module, service, _, _, _ = setup_service(monkeypatch, config, tmp_path)
    blocked = tmp_path / "npm" / "bin"
    monkeypatch.setattr(module.os, "access", lambda path, mode: Path(path) != blocked)
    result = await service.check()
    assert not item(result, "codex")["can_update"]
    assert "权限" in item(result, "codex")["reason"]


async def test_does_not_downgrade_newer_installed_version(monkeypatch, config, tmp_path):
    _, service, _, _, versions = setup_service(monkeypatch, config, tmp_path)
    versions["claude"] = "2.2.0"
    result = await service.check()
    assert not item(result, "claude")["update_available"]
    with pytest.raises(ValueError):
        await service.start("claude")


async def test_closing_idle_session_failure_prevents_installer(monkeypatch, config, tmp_path):
    _, service, runner, calls, _ = setup_service(monkeypatch, config, tmp_path)
    await service.check()
    async def fail():
        raise RuntimeError("session did not close")
    runner.close_idle_for_runtime_update = fail
    await service.start("claude")
    result = await finish(service)
    assert not runner.reserved
    assert "did not close" in item(result, "claude")["error"]
    assert all("install" not in call for call in calls)


@pytest.mark.parametrize("version", ["1.2.3;id", "1.2.3-beta.1", "１.２.３", "1.2.3\n", None])
def test_registry_version_requires_ascii_stable_semver(version):
    module = importlib.import_module("skill_runner.runtime_updates")
    with pytest.raises(ValueError):
        module._valid_version(version)


def test_claude_path_falls_back_to_sdk_bundled_executable(monkeypatch, tmp_path):
    paths = importlib.import_module("skill_runner.runtime_paths")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(paths.shutil, "which", lambda command: None)
    bundled = tmp_path / "sdk" / "_bundled" / ("claude.exe" if paths.os.name == "nt" else "claude")
    bundled.parent.mkdir(parents=True)
    bundled.touch()
    monkeypatch.setattr(paths.importlib.util, "find_spec", lambda name: SimpleNamespace(origin=str(tmp_path / "sdk" / "__init__.py")))
    assert paths.claude_cli_path(SimpleNamespace(claude_bin=None)) == str(bundled)
    bundled.unlink()
    assert paths.claude_cli_path(SimpleNamespace(claude_bin=None)) is None


async def test_installer_cannot_downgrade_runtime_updated_since_check(monkeypatch, config, tmp_path):
    _, service, runner, calls, versions = setup_service(monkeypatch, config, tmp_path)
    await service.check()
    versions["claude"] = "2.2.0"
    await service.start("claude")
    result = await finish(service)
    assert item(result, "claude")["status"] == "failed"
    assert not runner.reserved
    assert all("install" not in call for call in calls)


async def test_claude_migration_verifies_new_native_executable(monkeypatch, config, tmp_path):
    module, service, _, calls, _ = setup_service(monkeypatch, config, tmp_path)
    native = False
    monkeypatch.setattr(module, "claude_cli_path", lambda config: "/native/claude" if native else "/sdk/claude")
    original = module._command
    async def migrate(argv, timeout=15):
        nonlocal native
        if argv[0] not in {"/sdk/claude", "/native/claude"}:
            return await original(argv, timeout)
        calls.append(argv)
        if argv[1] == "install":
            native = True
            return "installed"
        return "2.1.310" if argv[0] == "/native/claude" else "2.1.300"
    monkeypatch.setattr(module, "_command", migrate)
    await service.check()
    await service.start("claude")
    result = await finish(service)
    assert item(result, "claude")["status"] == "succeeded"
    assert calls[-1] == ["/native/claude", "--version"]
