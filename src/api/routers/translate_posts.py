"""
Translate post/title endpoints.
"""

import asyncio
import logging
import os
import re

from fastapi import APIRouter, Request

from src.config.timeout_config import TimeoutConfig
from src.core.post_hashtags import (
    append_xiaohongshu_hashtags,
    normalize_xiaohongshu_hashtags,
)
from src.core.protected_terms import preserve_protected_terms
from src.prompts import get_prompt_manager
from ..middleware import BadRequestException
from ..middleware.rate_limit import limiter
from ..utils.llm_errors import raise_llm_service_unavailable
from ..utils.glossary import build_glossary_context
from ..utils.concurrency import run_blocking, run_llm_blocking
from ..utils.json_utils import parse_llm_json_response
from ..utils.llm_factory import generate_with_fallback
from .translate_models import (
    POST_OPTIMIZE_OPTIONS,
    GenerateTitleRequest,
    GenerateTitleResponse,
    PostHashtagRequest,
    PostHashtagResponse,
    PostOptimizeRequest,
    PostOptimizeResponse,
    PostTranslateRequest,
    PostTranslateResponse,
    resolve_post_optimize_instruction,
)


logger = logging.getLogger(__name__)

router = APIRouter()
prompt_manager = get_prompt_manager()


# BE-03：单次尝试超时与整体预算必须分开取值。两者相等时，第一次 attempt 卡满
# 就会被外层 wait_for 取消，config/llm_providers.yaml 里配置的多 key / 多模型
# 故障转移永远跑不到第二次。整体预算按「至少容纳 2-3 次尝试」取值。
# 注：更合适的归属地是 src/config/timeout_config.py，本次改动不拥有该文件，
# 先在调用侧收口，后续可整体上移。
# 整体预算必须**小于**前端 REQUEST_TIMEOUTS.POST_*（web/frontend/src/shared/
# constants.ts，当前 180s）：否则浏览器先断开，用户看不到服务端这条可读的 503，
# 而被放弃的线程还会继续占着线程池跑到预算耗尽。
_TIMEOUT_BUDGETS: dict[str, tuple[int, int]] = {
    # task_type: (单次尝试超时, 整体预算)
    # 帖子是短文本，60s 单次足够；170s 预算刚好容纳两次完整尝试 + 余量，
    # 且严格早于前端 180s 超时。
    "post": (60, 170),
    "post_optimize": (60, 170),
    "title_generate": (45, 120),
}

# BE-02：历史记录内容/角色未做任何长度与内容约束就拼进 prompt，这里压平空白并截断，
# 防止调用方用超长内容放大一次 LLM 调用，或在历史块里伪造出新的「## 」小节标题。
_HISTORY_CONTENT_MAX_LENGTH = 300
_HISTORY_ROLE_MAX_LENGTH = 20

# BE-02：GenerateTitleRequest.instruction 目前没有 max_length（对比
# PostOptimizeRequest.instruction 为 1000），这里在路由层兜底。
_TITLE_INSTRUCTION_MAX_LENGTH = 1000

# BE-07：前端对三个快捷优化按钮只记录 `[readable]` 这类内部 id，原样注入历史等于没有信息。
# 这里在服务端单点还原成一行摘要（完整正文见 translate_models.POST_OPTIMIZE_OPTIONS，
# 只注入摘要而非全文，避免 3 轮历史把 prompt 撑爆）。
_POST_OPTIMIZE_OPTION_SUMMARIES = {
    "readable": "上一轮要求：降低阅读负荷，一句一事、主语明确、先结论后解释",
    "idiomatic": "上一轮要求：让中文更自然地道，去连接词与套话，修辞不字面直译",
    "professional": "上一轮要求：提高信息密度与精准度，删口水话、不增不减",
}
_OPTION_ID_RE = re.compile(r"\[(\w+)\]")


def _resolve_timeouts(task_type: str) -> tuple[int, int]:
    """返回 (单次尝试超时, 整体预算)；整体预算严格大于单次尝试超时。"""
    fallback = TimeoutConfig.get_timeout(task_type)
    return _TIMEOUT_BUDGETS.get(task_type, (fallback, fallback * 3))


@router.post("/generate/hashtags", response_model=PostHashtagResponse)
@limiter.limit("30/minute")
async def generate_hashtags(request: Request, body: PostHashtagRequest):
    """Generate content-specific Xiaohongshu hashtags without broad padding."""

    prompt = prompt_manager.get(
        "post_hashtags",
        content=body.content,
        translation=body.translation,
    )
    attempt_timeout_s, total_timeout_s = _resolve_timeouts("title_generate")
    model_metadata: dict[str, object] = {}
    try:
        result = await asyncio.wait_for(
            run_llm_blocking(
                generate_with_fallback,
                prompt,
                task_type="title",
                timeout=attempt_timeout_s,
                model=body.model,
                result_metadata=model_metadata,
            ),
            timeout=total_timeout_s,
        )
        data = parse_llm_json_response(result)
        candidates = data.get("tags", []) if isinstance(data, dict) else []
        tags = normalize_xiaohongshu_hashtags(
            candidates if isinstance(candidates, list) else [],
            body.content,
            body.translation,
        )
        return PostHashtagResponse(
            tags=tags,
            model_used=model_metadata.get("model_used"),
            provider_used=model_metadata.get("provider_used"),
            fallback_used=bool(model_metadata.get("fallback_used", False)),
        )
    except asyncio.TimeoutError as error:
        raise_llm_service_unavailable(
            operation="Hashtag generation",
            exc=error,
            timeout_s=total_timeout_s,
        )
    except Exception as error:
        raise_llm_service_unavailable(
            operation="Hashtag generation",
            exc=error,
            timeout_s=total_timeout_s,
        )


@router.post("/translate/post", response_model=PostTranslateResponse)
@limiter.limit("20/minute")
async def translate_post(request: Request, body: PostTranslateRequest):
    """Translate a post to Chinese."""
    if not body.content.strip():
        raise BadRequestException(detail="Content cannot be empty")

    # 公网环境禁用 custom_prompt（防止 prompt 注入）
    if body.custom_prompt:
        if not os.getenv("ALLOW_CUSTOM_PROMPTS", "false").lower() == "true":
            raise BadRequestException(detail="Custom prompts are not allowed in production")

    glossary_context = await run_blocking(build_glossary_context, body.content)

    if body.custom_prompt:
        prompt = body.custom_prompt.replace("{content}", body.content)
        prompt = prompt.replace("{glossary}", glossary_context)
    else:
        prompt = prompt_manager.get(
            "post_translation",
            text=body.content,
            dynamic_sections=glossary_context.strip(),
        )

    attempt_timeout_s, total_timeout_s = _resolve_timeouts("post")
    # BE-06：try 只包住 LLM 调用本身，后处理失败不再被当成「LLM 服务不可用」。
    try:
        model_metadata: dict[str, object] = {}
        translation = await asyncio.wait_for(
            run_llm_blocking(
                generate_with_fallback,
                prompt,
                task_type="post",
                timeout=attempt_timeout_s,
                model=body.model,
                result_metadata=model_metadata,
            ),
            timeout=total_timeout_s,
        )
        # BE-05：上游返回 None / 空串时不能 200 返回空译文（这样写同时覆盖 None，
        # 避免 .strip() 抛 AttributeError 把内部错误文本回传出去）。
        if not (translation or "").strip():
            raise ValueError("LLM returned empty translation")
    except asyncio.TimeoutError as e:
        raise_llm_service_unavailable(operation="Translation", exc=e, timeout_s=total_timeout_s)
    except Exception as e:
        raise_llm_service_unavailable(operation="Translation", exc=e, timeout_s=total_timeout_s)

    translation = translation.strip()
    # BE-06：后处理只做 token 守卫与标签整理，出错时降级返回原始模型输出，
    # 不丢弃已经生成（且已付费）的译文。
    try:
        translation = preserve_protected_terms(body.content, translation)
        translation = append_xiaohongshu_hashtags(translation, body.content)
    except Exception:
        logger.exception("Post-processing failed for /translate/post; returning raw model output")
    return PostTranslateResponse(
        translation=translation,
        model_used=model_metadata.get("model_used"),
        provider_used=model_metadata.get("provider_used"),
        fallback_used=bool(model_metadata.get("fallback_used", False)),
    )


@router.post("/translate/post/optimize", response_model=PostOptimizeResponse)
@limiter.limit("20/minute")
async def optimize_post_translation(request: Request, body: PostOptimizeRequest):
    """Optimize an existing translation."""
    if not body.current_translation.strip():
        raise BadRequestException(detail="Current translation cannot be empty")

    resolved_instruction = resolve_post_optimize_instruction(
        body.instruction, body.option_id
    )
    if not resolved_instruction:
        raise BadRequestException(
            detail="Either instruction or a valid option_id must be provided"
        )

    glossary_context = await run_blocking(
        build_glossary_context,
        body.original_text,
    )

    # C21:conversation_history 此前被前端发送、被校验,却从未注入 prompt(多轮优化上下文失效)。
    # 这里把最近几轮调整格式化为参考上下文传入。值里的花括号由 str.format 安全处理(不二次解析)。
    history_section = ""
    if body.conversation_history:
        _hist_lines = ["## 历史调整记录(供参考,理解用户连续优化的意图)"]
        for _item in list(body.conversation_history)[-3:]:
            if isinstance(_item, dict):
                _role = _item.get("role", "")
                _content = _item.get("content") or _item.get("instruction") or ""
            else:
                _role = getattr(_item, "role", "")
                _content = getattr(_item, "content", "") or getattr(_item, "instruction", "")
            # BE-02：压平空白并截断，防止超长历史放大调用成本或伪造小节标题。
            _content = " ".join(str(_content).split())[:_HISTORY_CONTENT_MAX_LENGTH]
            if not _content:
                continue
            # BE-07：把 `[readable]` 这类快捷选项 id 还原成一行可读摘要。
            _matched = _OPTION_ID_RE.fullmatch(_content)
            if _matched and _matched.group(1) in POST_OPTIMIZE_OPTIONS:
                _content = _POST_OPTIMIZE_OPTION_SUMMARIES.get(_matched.group(1), _content)
            _role = " ".join(str(_role).split())[:_HISTORY_ROLE_MAX_LENGTH] or "user"
            _hist_lines.append(f"- [{_role}] {_content}")
        if len(_hist_lines) > 1:
            history_section = "\n".join(_hist_lines)

    prompt = prompt_manager.get(
        "post_optimize",
        glossary_section=glossary_context.strip(),
        conversation_history_section=history_section,
        original_text=body.original_text,
        current_translation=body.current_translation,
        instruction=resolved_instruction,
    )

    attempt_timeout_s, total_timeout_s = _resolve_timeouts("post_optimize")
    # BE-06：try 只包住 LLM 调用本身。
    try:
        model_metadata: dict[str, object] = {}
        optimized = await asyncio.wait_for(
            run_llm_blocking(
                generate_with_fallback,
                prompt,
                task_type="post",
                timeout=attempt_timeout_s,
                model=body.model,
                result_metadata=model_metadata,
            ),
            timeout=total_timeout_s,
        )
        # BE-05：上游返回 None / 空串时不能 200 返回空译文。
        if not (optimized or "").strip():
            raise ValueError("LLM returned empty optimized translation")
    except asyncio.TimeoutError as e:
        raise_llm_service_unavailable(operation="Optimization", exc=e, timeout_s=total_timeout_s)
    except Exception as e:
        raise_llm_service_unavailable(operation="Optimization", exc=e, timeout_s=total_timeout_s)

    optimized = optimized.strip()
    # BE-06：后处理失败时降级返回原始模型输出，不丢弃已生成的结果。
    try:
        optimized = preserve_protected_terms(body.original_text, optimized)
        # 优化路径不再自动补推荐标签：用户可能正是要求「去掉话题标签」，
        # 但已有标签的去重/去违禁词/截断仍需保留。
        optimized = append_xiaohongshu_hashtags(
            optimized, body.original_text, allow_recommend=False
        )
    except Exception:
        logger.exception(
            "Post-processing failed for /translate/post/optimize; returning raw model output"
        )
    return PostOptimizeResponse(
        optimized_translation=optimized,
        model_used=model_metadata.get("model_used"),
        provider_used=model_metadata.get("provider_used"),
        fallback_used=bool(model_metadata.get("fallback_used", False)),
    )


@router.post("/generate/title", response_model=GenerateTitleResponse)
@limiter.limit("20/minute")
async def generate_title(request: Request, body: GenerateTitleRequest):
    """Generate 6 title options in JSON format."""
    if not body.content.strip():
        raise BadRequestException(detail="Content cannot be empty")

    # BE-02：instruction 在模型层没有长度上限，这里兜底拒绝超长指令，避免一次请求
    # 就把无上限文本灌进 prompt 放大 LLM 调用成本。
    if body.instruction and len(body.instruction) > _TITLE_INSTRUCTION_MAX_LENGTH:
        raise BadRequestException(
            detail=f"Instruction is too long (max {_TITLE_INSTRUCTION_MAX_LENGTH} characters)"
        )

    normalized_instruction = (
        (body.instruction or "").strip()
        or "在忠实内容的前提下，尽量更有吸引力、更有记忆点。"
    )
    prompt = prompt_manager.get(
        "post_title",
        content=body.content,
        instruction=normalized_instruction,
    )

    attempt_timeout_s, total_timeout_s = _resolve_timeouts("title_generate")
    try:
        model_metadata: dict[str, object] = {}
        result = await asyncio.wait_for(
            run_llm_blocking(
                generate_with_fallback,
                prompt,
                task_type="title",
                timeout=attempt_timeout_s,
                model=body.model,
                result_metadata=model_metadata,
            ),
            timeout=total_timeout_s,
        )
        data = parse_llm_json_response(result)
        titles = [
            data.get("suspense", ""),
            data.get("data", ""),
            data.get("counter_intuitive", ""),
            data.get("pain_point", ""),
            data.get("minimal", ""),
            data.get("contrast", ""),
            data.get("free_1", ""),
            data.get("free_2", ""),
        ]
        titles = [title for title in titles if title]
        if not titles:
            # LLM 输出被截断或不可解析时 parse_llm_json_response 返回 {}，
            # 这里显式失败，交给下面的 except 统一转成 503，避免 200 返回空标题。
            raise ValueError("LLM returned unparseable or empty title JSON")
        return GenerateTitleResponse(
            title="\n".join(titles),
            model_used=model_metadata.get("model_used"),
            provider_used=model_metadata.get("provider_used"),
            fallback_used=bool(model_metadata.get("fallback_used", False)),
        )
    except asyncio.TimeoutError as e:
        raise_llm_service_unavailable(operation="Title generation", exc=e, timeout_s=total_timeout_s)
    except Exception as e:
        raise_llm_service_unavailable(operation="Title generation", exc=e, timeout_s=total_timeout_s)
