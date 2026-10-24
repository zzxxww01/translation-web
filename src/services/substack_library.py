"""服务器上存的一份 SemiAnalysis 文章清单，每篇配中文标题和一句话摘要。

打开文章库时直接读这份清单，只去 Substack 看一眼最新一页有没有新文章；中文标题和
摘要由最便宜的模型在后台分批生成，每篇只生成一次，结果和清单存在一起。
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from src.core.file_utils import read_json, write_json_atomic
from src.llm.errors import LLMOutputTruncatedError

from .substack_service import ArchivePost, SubstackClient

logger = logging.getLogger(__name__)

ARCHIVE_PAGE_SIZE = 25  # Substack 每次最多返回约 25 篇，要得再多也一样
MAX_SYNC_PAGES = 100  # 上游行为异常时不至于无限翻页；目前全部文章约 15 页
DIGEST_BATCH_SIZE = 10  # 带思考的 flash 模型一批 20 篇会撞上输出长度上限
MAX_DIGEST_ATTEMPTS = 3  # 模型回复里一直漏掉某篇时，最多试几次
DIGEST_RETRY_DELAY_SECONDS = 600  # 模型调用本身出错（多半是服务暂时不可用）后，隔多久再试
DIGEST_OPENING_CHARS = 600


@dataclass
class LibraryPost:
    title: str
    subtitle: str
    slug: str
    url: str
    post_date: str
    is_paid: bool
    cover_image: Optional[str]
    wordcount: Optional[int]
    excerpt: str = ""
    zh_title: str = ""
    zh_summary: str = ""
    digest_attempts: int = 0

    @classmethod
    def from_archive(cls, post: ArchivePost, previous: Optional["LibraryPost"] = None) -> "LibraryPost":
        merged = cls(**post.to_dict())
        # 标题或副标题改过的文章，旧的中文就不对了，重新生成
        if previous and (previous.title, previous.subtitle) == (post.title, post.subtitle):
            merged.zh_title = previous.zh_title
            merged.zh_summary = previous.zh_summary
            merged.digest_attempts = previous.digest_attempts
        return merged

    @classmethod
    def from_dict(cls, data: dict) -> "LibraryPost":
        known = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in known})

    @property
    def needs_digest(self) -> bool:
        return not self.zh_title and self.digest_attempts < MAX_DIGEST_ATTEMPTS

    def matches(self, words: Sequence[str]) -> bool:
        haystack = " ".join((self.title, self.subtitle, self.zh_title, self.zh_summary, self.excerpt)).lower()
        return all(word in haystack for word in words)


# 输入一批文章，返回 slug → {"zh_title": ..., "zh_summary": ...}；没给出的视为这次失败
DigestFn = Callable[[Sequence[LibraryPost]], Dict[str, Dict[str, str]]]


class SubstackLibrary:
    def __init__(
        self,
        store_path: Path,
        client_factory: Callable[[], SubstackClient],
        digest_fn: Optional[DigestFn] = None,
    ):
        self.store_path = Path(store_path)
        self._client_factory = client_factory
        self._digest_fn = digest_fn
        self._lock = threading.Lock()  # 保护内存里的清单和落盘
        self._sync_lock = threading.Lock()  # 同一时间只同步一次
        self._digest_thread: Optional[threading.Thread] = None
        self._digest_retry_at = 0.0
        self._posts: Optional[Dict[str, LibraryPost]] = None
        self._synced_at: Optional[str] = None

    # ---------- 读 ----------

    def _loaded(self) -> Dict[str, LibraryPost]:
        """调用方须持有 self._lock。"""
        if self._posts is None:
            self._posts = {}
            if self.store_path.exists():
                try:
                    data = read_json(self.store_path)
                    for item in data.get("posts", []):
                        post = LibraryPost.from_dict(item)
                        self._posts[post.slug] = post
                    self._synced_at = data.get("synced_at")
                except (OSError, ValueError, TypeError, AttributeError) as exc:
                    logger.warning("文章清单文件损坏，将重新拉取：%s", exc)
                    self._posts = {}
        return self._posts

    def _save(self) -> None:
        """调用方须持有 self._lock。"""
        posts = sorted(self._loaded().values(), key=lambda post: post.post_date, reverse=True)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(
            self.store_path,
            {"synced_at": self._synced_at, "posts": [asdict(post) for post in posts]},
        )

    def count(self) -> int:
        with self._lock:
            return len(self._loaded())

    def posts(self, search: str = "") -> List[LibraryPost]:
        """按发布时间从新到旧；搜索词之间是「且」的关系，中英文都查。"""
        words = search.lower().split()
        with self._lock:
            matched = [post for post in self._loaded().values() if post.matches(words)]
        return sorted(matched, key=lambda post: post.post_date, reverse=True)

    def pending_digests(self) -> int:
        with self._lock:
            return sum(1 for post in self._loaded().values() if post.needs_digest)

    # ---------- 同步 ----------

    def ensure_synced(self) -> None:
        """清单还是空的（第一次打开）就把全部文章拉一遍。"""
        if self.count() == 0:
            self.sync(full=True)

    def sync(self, *, full: bool = False) -> int:
        """从 Substack 拉清单，返回新增篇数。

        平时只看最新一页，碰到已经存过的文章就停；full 会把全部文章重新拉一遍，
        顺带去掉 Substack 上已经删掉的文章。
        """
        with self._sync_lock:
            with self._lock:
                known = set(self._loaded())
            fetched = self._fetch(stop_at_known=None if full else known)
            with self._lock:
                current = self._loaded()
                added = sum(1 for slug in fetched if slug not in current)
                if full:
                    self._posts = {slug: LibraryPost.from_archive(post, current.get(slug)) for slug, post in fetched.items()}
                else:
                    for slug, post in fetched.items():
                        current[slug] = LibraryPost.from_archive(post, current.get(slug))
                self._synced_at = datetime.now(timezone.utc).isoformat()
                self._save()
            return added

    def _fetch(self, stop_at_known: Optional[set]) -> Dict[str, ArchivePost]:
        client = self._client_factory()
        fetched: Dict[str, ArchivePost] = {}
        offset = 0
        for _ in range(MAX_SYNC_PAGES):
            page = client.list_archive(offset=offset, limit=ARCHIVE_PAGE_SIZE)
            new = [post for post in page if post.slug not in fetched]
            for post in new:
                fetched[post.slug] = post
            # 部分文章对当前登录身份不可见时，一页的实收条数会少于请求条数；按实收
            # 条数推进可能与下一页重叠，靠 slug 去重，但不会漏掉文章
            offset += len(page)
            if not new:
                break
            if stop_at_known is not None and any(post.slug in stop_at_known for post in page):
                break
        return fetched

    # ---------- 中文标题和摘要 ----------

    def digest_running(self) -> bool:
        with self._lock:
            return self._digest_thread is not None and self._digest_thread.is_alive()

    def start_digest_worker(self) -> None:
        """有待生成的文章就在后台开一个线程去生成；已经在跑、或刚出错还在等待时不开。"""
        if self._digest_fn is None or time.monotonic() < self._digest_retry_at or self.pending_digests() == 0:
            return
        with self._lock:
            if self._digest_thread is not None and self._digest_thread.is_alive():
                return
            self._digest_thread = threading.Thread(
                target=self.generate_digests, name="substack-digest", daemon=True
            )
            self._digest_thread.start()

    def generate_digests(self) -> int:
        """分批生成，返回这次生成成功的篇数。

        模型调用出错时先停下，过一阵再试，不计入单篇的重试次数——否则模型服务短暂
        不可用就会让所有文章都被放弃。
        """
        if self._digest_fn is None:
            return 0
        done = 0
        batch_size = DIGEST_BATCH_SIZE
        while True:
            with self._lock:
                pending = sorted(
                    (post for post in self._loaded().values() if post.needs_digest),
                    key=lambda post: post.post_date,
                    reverse=True,
                )
                batch = [LibraryPost.from_dict(asdict(post)) for post in pending[:batch_size]]
            if not batch:
                return done
            try:
                results = self._digest_fn(batch)
            except LLMOutputTruncatedError:
                # 回复太长被截断不是服务故障，冷却后重试同一批还会截断、卡住后面所有
                # 文章：这一轮改用小批；只剩一篇仍被截断就算这篇失败一次
                if len(batch) > 1:
                    batch_size = max(1, len(batch) // 2)
                    continue
                results = {}
            except Exception:
                logger.exception("生成中文标题和摘要失败，%d 秒后再试", DIGEST_RETRY_DELAY_SECONDS)
                self._digest_retry_at = time.monotonic() + DIGEST_RETRY_DELAY_SECONDS
                return done
            with self._lock:
                current = self._loaded()
                for sent in batch:
                    post = current.get(sent.slug)
                    if post is None or post.title != sent.title:
                        continue  # 生成期间清单刷新过，这篇换了内容，结果作废
                    result = results.get(sent.slug)
                    if result:
                        post.zh_title = result["zh_title"]
                        post.zh_summary = result.get("zh_summary", "")
                        done += 1
                    else:
                        post.digest_attempts += 1
                self._save()


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")
# 便宜模型常无视「不要以本文开头」，直接去掉
_SUMMARY_PREFIX = re.compile(r"^(?:本文|文章|该文)\s*")


def parse_digest_response(raw: str) -> Dict[str, Dict[str, str]]:
    """解析模型返回的 JSON 数组；格式不对的条目直接丢掉，算这篇这次失败。"""
    try:
        data = json.loads(_FENCE.sub("", (raw or "").strip()))
    except ValueError:
        return {}
    if isinstance(data, dict):
        data = data.get("articles", [])
    results: Dict[str, Dict[str, str]] = {}
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        slug, zh_title = item.get("slug"), item.get("zh_title")
        if isinstance(slug, str) and isinstance(zh_title, str) and zh_title.strip():
            summary = item.get("zh_summary")
            results[slug] = {
                "zh_title": zh_title.strip()[:100],
                "zh_summary": _SUMMARY_PREFIX.sub("", summary.strip())[:300] if isinstance(summary, str) else "",
            }
    return results


def make_llm_digest_fn(task_type: str = "metadata") -> DigestFn:
    """用任务默认模型（metadata 任务走最便宜的 flash 档）批量生成，不带术语表。"""
    llm = None

    def digest(posts: Sequence[LibraryPost]) -> Dict[str, Dict[str, str]]:
        nonlocal llm
        from src.llm.factory import create_llm_provider, get_task_model_alias
        from src.prompts import get_prompt_manager

        if llm is None:
            llm = create_llm_provider(provider=get_task_model_alias(task_type))
        articles = [
            {
                "slug": post.slug,
                "title": post.title,
                "subtitle": post.subtitle,
                "opening": post.excerpt[:DIGEST_OPENING_CHARS],
            }
            for post in posts
        ]
        prompt = get_prompt_manager().render(
            "substack_digest", articles_json=json.dumps(articles, ensure_ascii=False, indent=1)
        )
        return parse_digest_response(llm.generate(prompt, response_format="json", temperature=0.3))

    return digest
