"""部署自检：起一个真实的 Claude 会话，走一遍「提问 → 作答 → Bash → 写文件 → 结束」。

    python -m skill_runner.smoke

用的是和服务完全一样的配置与权限策略（读同样的环境变量），运行目录建在临时目录里，跑完删除。
会消耗少量订阅额度。退出码 0 表示通过。
"""

from __future__ import annotations

import asyncio
import dataclasses
import sys
import tempfile
from pathlib import Path

from .config import Config
from .runner import Runner
from .sdk_session import make_factory
from .store import RunStore

PROMPT = """这是 skill-runner 的部署自检，请严格按顺序做，不要做别的事：
1. 用 AskUserQuestion 工具问我一个单选题「自检选哪个？」，选项为「甲」和「乙」。
2. 用 Bash 执行：echo bash-ok > bash.txt
3. 用 Write 工具在当前目录写 answer.txt，内容只有我选的那个选项。
4. 回复「自检完成」。"""

TIMEOUT_S = 300


async def run_smoke(config: Config) -> bool:
    store = RunStore(config.runs_dir)
    runner = Runner(config, store, make_factory(config))
    meta = runner.create("", "自检")
    _, queue = runner.subscribe(meta.id)
    answered = None
    try:
        await runner.send_message(meta.id, PROMPT, [])
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=TIMEOUT_S)
            kind = event["type"]
            detail = event.get("text") or event.get("summary") or event.get("status") or ""
            print(f"[{event['seq']:>3}] {kind:<11} {str(detail)[:100]}")
            if kind == "question":
                answered = {q["question"]: q["options"][0]["label"] for q in event["questions"]}
                runner.answer(meta.id, event["qid"], answered)
            if kind == "status" and event["status"] in {"idle", "error"}:
                break
    finally:
        await runner.shutdown()

    run_dir = store.run_dir(meta.id)
    answer_file = run_dir / "answer.txt"
    checks = {
        "会话正常结束": runner.meta(meta.id).status == "idle",
        "提问经网页作答": answered is not None,
        "Bash 在运行目录写文件": (run_dir / "bash.txt").is_file(),
        "Write 写入作答结果": answer_file.is_file()
        and answered is not None
        and answer_file.read_text(encoding="utf-8").strip() in answered.values(),
        "拿到会话 ID（可续接）": bool(runner.meta(meta.id).session_id),
    }
    for name, ok in checks.items():
        print(f"{'通过' if ok else '失败'}  {name}")
    return all(checks.values())


def main() -> int:
    base = Config.from_env()
    with tempfile.TemporaryDirectory(prefix="skill-runner-smoke-") as tmp:
        config = dataclasses.replace(base, home=Path(tmp))
        ok = asyncio.run(run_smoke(config))
    print("自检通过" if ok else "自检失败")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
