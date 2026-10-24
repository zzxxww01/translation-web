# -*- coding: utf-8 -*-
"""用自己的订阅登录态下载 Substack 文章 HTML（含付费文章）。

网站上「SemiAnalysis 文章」页和新建项目弹窗里的链接导入用的是同一套逻辑
（`src/services/substack_service.py`），这个脚本只是命令行入口。

下载下来的就是文章页的服务端 HTML，正文在 `div.available-content`，
可以直接交给 `src/core/parser.py` 或 four-step-translate 使用。

Cookie（任选其一，前者优先）：
    - 网站上填写过的（存在 data/substack_cookie.txt）；
    - .env 里的 SUBSTACK_COOKIE。浏览器登录后打开任意一篇文章 → F12 → Network
      → 刷新 → 点第一条文档请求 → Request Headers 里的 `cookie:`，整行复制进去即可，
      会自动挑出登录会话那一项：自定义域名（如 newsletter.semianalysis.com）下是
      `connect.sid`，*.substack.com 下是 `substack.sid`。
    cookie 只会发给 SUBSTACK_COOKIE_DOMAIN（默认 newsletter.semianalysis.com）。

用法：
    python scripts/fetch_substack.py <文章链接> [<文章链接> ...]
    python scripts/fetch_substack.py -f urls.txt            # 每行一个链接，# 开头为注释
    python scripts/fetch_substack.py <链接> -o D:/articles   # 默认存到 data/substack_html/

下载到的页面若带付费墙（未登录或 cookie 失效），不保存并以非零退出码结束，
避免把截断的正文送进翻译流程。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.services.substack_service import (  # noqa: E402
    DEFAULT_COOKIE_DOMAIN,
    SubstackClient,
    SubstackCookieStore,
    SubstackError,
)

DEFAULT_OUT_DIR = REPO_ROOT / "data" / "substack_html"
REQUEST_INTERVAL_SECONDS = 1.5


def read_url_file(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def main() -> int:
    parser = argparse.ArgumentParser(description="下载 Substack 文章 HTML（含付费文章）")
    parser.add_argument("urls", nargs="*", help="文章链接")
    parser.add_argument("-f", "--file", type=Path, help="链接列表文件，每行一个")
    parser.add_argument("-o", "--out-dir", type=Path, default=DEFAULT_OUT_DIR, help=f"保存目录（默认 {DEFAULT_OUT_DIR}）")
    args = parser.parse_args()

    urls = list(args.urls)
    if args.file:
        urls += read_url_file(args.file)
    if not urls:
        parser.error("至少给一个文章链接，或用 -f 指定链接列表文件")

    store = SubstackCookieStore(
        cookie_file=REPO_ROOT / "data" / "substack_cookie.txt",
        env_file=REPO_ROOT / ".env",
        domain=os.environ.get("SUBSTACK_COOKIE_DOMAIN", DEFAULT_COOKIE_DOMAIN),
    )
    if not store.is_configured():
        print("警告：未配置订阅 cookie，付费文章只能拿到截断版本", file=sys.stderr)
    client = SubstackClient(store)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for i, raw_url in enumerate(urls):
        if i:
            time.sleep(REQUEST_INTERVAL_SECONDS)
        try:
            article = client.fetch_article(raw_url)
        except SubstackError as exc:
            print(f"[失败] {raw_url}：{exc.message}", file=sys.stderr)
            failures += 1
            continue

        out_path = args.out_dir / f"{article.slug}.html"
        out_path.write_text(article.html, encoding="utf-8")
        print(f"[完成] {article.url} → {out_path}（{len(article.html) // 1024} KB）")

    print(f"共 {len(urls)} 篇，成功 {len(urls) - failures}，失败 {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
