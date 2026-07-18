"""SSE session helper for longform translation flows."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any, Awaitable, Callable, Dict
from uuid import uuid4


logger = logging.getLogger(__name__)

_conflict_lock = threading.Lock()
_pending_conflict_events: Dict[str, Dict[str, asyncio.Event]] = {}
_conflict_resolutions: Dict[str, Dict[str, Dict[str, Any]]] = {}
_conflict_session_owners: Dict[str, str] = {}


def resolve_live_conflict(project_id: str, term: str, chosen_translation: str, apply_to_all: bool) -> bool:
    """Store a live conflict resolution and wake any waiting translation task."""
    with _conflict_lock:
        events = _pending_conflict_events.get(project_id, {})
        resolutions = _conflict_resolutions.setdefault(project_id, {})
        term_key = term.lower()
        resolutions[term_key] = {
            "chosen_translation": chosen_translation,
            "apply_to_all": apply_to_all,
        }
        event = events.get(term_key)

    if event:
        event.set()
        return True
    return False


class TranslationStreamSession:
    """Bridge a translation coroutine to SSE with heartbeats and live conflicts."""

    def __init__(
        self,
        *,
        project_id: str,
        request,
        total_paragraphs: int,
        total_sections: int,
        run_translation: Callable[[Callable[[str, int, int], None], Callable[[Any], Awaitable[Dict[str, Any]]]], Awaitable[Dict[str, Any]]],
        cancel_translation: Callable[[str], Awaitable[Dict[str, Any]]],
        release_slot: Callable[[str], None],
    ):
        self.project_id = project_id
        self.request = request
        self.total_paragraphs = total_paragraphs
        self.total_sections = total_sections
        self._run_translation = run_translation
        self._cancel_translation = cancel_translation
        self._release_slot = release_slot
        self._progress_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._event_loop = asyncio.get_running_loop()
        self._client_attached = True
        self._translation_task: asyncio.Task | None = None
        self._conflict_prompt_lock = asyncio.Lock()
        self._resolved_conflicts: Dict[str, Dict[str, Any]] = {}
        self._session_id = uuid4().hex

    def _init_conflict_state(self) -> None:
        with _conflict_lock:
            _conflict_session_owners[self.project_id] = self._session_id
            _pending_conflict_events[self.project_id] = {}
            _conflict_resolutions[self.project_id] = {}

    def _clear_conflict_state(self) -> None:
        with _conflict_lock:
            if _conflict_session_owners.get(self.project_id) != self._session_id:
                return
            _conflict_session_owners.pop(self.project_id, None)
            _pending_conflict_events.pop(self.project_id, None)
            _conflict_resolutions.pop(self.project_id, None)

    async def _handle_term_conflict_on_main(self, conflict) -> Dict[str, Any]:
        def default_resolution() -> Dict[str, Any]:
            return {
                "chosen_translation": (
                    conflict.existing_translation
                    or conflict.new_translation
                ),
                "apply_to_all": True,
            }

        term_key = conflict.term.lower()
        async with self._conflict_prompt_lock:
            cached = self._resolved_conflicts.get(term_key)
            if cached is not None:
                return dict(cached)
            if not self._client_attached:
                return default_resolution()

            event = asyncio.Event()
            with _conflict_lock:
                if (
                    _conflict_session_owners.get(self.project_id)
                    != self._session_id
                ):
                    return default_resolution()
                _pending_conflict_events[self.project_id][term_key] = event
                if not self._client_attached:
                    _pending_conflict_events[self.project_id].pop(term_key, None)
                    return default_resolution()
            await self._progress_queue.put(
                {
                    "type": "term_conflict",
                    "conflict": conflict.model_dump(mode="json"),
                }
            )
            try:
                await event.wait()
                with _conflict_lock:
                    resolution = _conflict_resolutions.get(
                        self.project_id, {}
                    ).get(term_key, {})
                result = {
                    "chosen_translation": resolution.get("chosen_translation")
                    or conflict.existing_translation
                    or conflict.new_translation,
                    "apply_to_all": resolution.get("apply_to_all", True),
                }
                if result["apply_to_all"]:
                    self._resolved_conflicts[term_key] = dict(result)
                return result
            finally:
                with _conflict_lock:
                    _pending_conflict_events.get(self.project_id, {}).pop(
                        term_key, None
                    )
                    _conflict_resolutions.get(self.project_id, {}).pop(
                        term_key, None
                    )

    def _detach_client(self, reason: str) -> None:
        if not self._client_attached:
            return

        self._client_attached = False
        logger.info(
            "[%s] SSE client detached; translation will continue in background: %s",
            self.project_id,
            reason,
        )
        with _conflict_lock:
            if _conflict_session_owners.get(self.project_id) != self._session_id:
                return
            for event in _pending_conflict_events.get(self.project_id, {}).values():
                event.set()

    async def _run_translation_task(self) -> None:
        try:
            def on_progress(step: str, current: int, total: int) -> None:
                self._event_loop.call_soon_threadsafe(
                    self._progress_queue.put_nowait,
                    {
                        "type": "progress",
                        "step": step,
                        "current": current,
                        "total": total,
                        "message": step,
                    },
                )

            async def on_term_conflict(conflict) -> Dict[str, Any]:
                future = asyncio.run_coroutine_threadsafe(
                    self._handle_term_conflict_on_main(conflict),
                    self._event_loop,
                )
                return await asyncio.wrap_future(future)

            result = await self._run_translation(on_progress, on_term_conflict)
            status = result.get("status")
            if status == "completed":
                event_type = "complete"
            elif status == "cancelled":
                event_type = "cancelled"
            else:
                event_type = "incomplete"

            if event_type == "complete":
                message = (
                    f"Translation complete: "
                    f"{result.get('translated_paragraphs', 0)}/{self.total_paragraphs} paragraphs usable"
                )
            elif event_type == "cancelled":
                message = result.get("message") or "Translation cancelled"
            else:
                message = result.get("error") or (
                    f"Translation incomplete: "
                    f"{result.get('translated_paragraphs', 0)}/{self.total_paragraphs} paragraphs usable"
                )

            await self._progress_queue.put(
                {
                    "type": event_type,
                    "translated_count": result.get("translated_paragraphs", 0),
                    "total": self.total_paragraphs,
                    "result": result,
                    "message": message,
                }
            )
        except Exception as exc:
            await self._progress_queue.put({"type": "error", "error": str(exc)})
        finally:
            self._clear_conflict_state()
            self._release_slot(self.project_id)

    async def generate(self):
        translation_finished = False

        self._init_conflict_state()
        # Start the worker before exposing the first SSE frame. A client may
        # close immediately after reading "start"; the translation and slot
        # cleanup must still have an owning task in that case.
        self._translation_task = asyncio.create_task(self._run_translation_task())
        try:
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "start",
                        "total": self.total_paragraphs,
                        "total_sections": self.total_sections,
                        "message": "开始四步法翻译",
                    }
                )
                + "\n\n"
            )

            while True:
                if await self.request.is_disconnected():
                    self._detach_client("client disconnected")
                    break
                try:
                    event = await asyncio.wait_for(self._progress_queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") in ("complete", "error", "incomplete", "cancelled"):
                        translation_finished = True
                        break
                except asyncio.TimeoutError:
                    if await self.request.is_disconnected():
                        self._detach_client("client disconnected during heartbeat")
                        break
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

                    if self._translation_task.done():
                        if self._translation_task.exception():
                            yield (
                                "data: "
                                + json.dumps(
                                    {
                                        "type": "error",
                                        "error": str(self._translation_task.exception()),
                                    }
                                )
                                + "\n\n"
                            )
                        translation_finished = True
                        break
        except asyncio.CancelledError:
            self._detach_client("stream task cancelled")
            raise
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
        finally:
            if (
                not translation_finished
                and self._translation_task is not None
                and not self._translation_task.done()
            ):
                self._detach_client("stream closed before translation finished")
