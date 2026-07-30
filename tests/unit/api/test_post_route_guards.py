# -*- coding: utf-8 -*-
"""帖子路由的护栏：超时预算、优化选项摘要、话题标签开关。

这些都是「加了但没有任何断言保证它继续成立」的地方——将来改一处漏一处时，
失效是静默的（接口照常 200，只是约束消失）。
"""

import pytest

from src.api.routers import translate_posts
from src.core.post_hashtags import append_xiaohongshu_hashtags


# --- 超时预算 -----------------------------------------------------------

# 前端 REQUEST_TIMEOUTS.POST_* = 180s（web/frontend/src/shared/constants.ts）
_FRONTEND_POST_TIMEOUT_S = 180


@pytest.mark.parametrize("task_type", ["post", "post_optimize", "title_generate"])
def test_total_budget_exceeds_single_attempt(task_type):
    """整体预算必须严格大于单次尝试，否则故障转移永远跑不到第二次。"""
    attempt, total = translate_posts._resolve_timeouts(task_type)
    assert total > attempt


@pytest.mark.parametrize("task_type", ["post", "post_optimize", "title_generate"])
def test_total_budget_fits_within_frontend_timeout(task_type):
    """服务端必须先于浏览器超时，用户才能看到可读的 503 而非裸中断。"""
    _, total = translate_posts._resolve_timeouts(task_type)
    assert total < _FRONTEND_POST_TIMEOUT_S


def test_unknown_task_type_still_gets_a_larger_total():
    attempt, total = translate_posts._resolve_timeouts("does-not-exist")
    assert total > attempt


# --- 优化选项摘要 -------------------------------------------------------


def test_option_summaries_cover_every_optimize_option():
    """摘要表漏掉新选项时，历史里会静默退回裸 `[newid]`——正是它要修的 bug。"""
    from src.api.routers.translate_models import POST_OPTIMIZE_OPTIONS

    assert set(POST_OPTIMIZE_OPTIONS) == set(
        translate_posts._POST_OPTIMIZE_OPTION_SUMMARIES
    )


def test_option_id_pattern_only_matches_bare_ids():
    assert translate_posts._OPTION_ID_RE.fullmatch("[readable]")
    assert not translate_posts._OPTION_ID_RE.fullmatch("x[readable]")
    assert not translate_posts._OPTION_ID_RE.fullmatch("[readable] 请再简化")


# --- 话题标签开关 -------------------------------------------------------


def test_optimize_path_does_not_re_append_recommended_tags():
    """用户说「去掉标签」时，优化路径不得把推荐标签贴回去。"""
    text = "英伟达又涨了。"
    with_recommend = append_xiaohongshu_hashtags(
        text, "NVIDIA stock rose again on AI chip demand.", allow_recommend=True
    )
    without_recommend = append_xiaohongshu_hashtags(
        text, "NVIDIA stock rose again on AI chip demand.", allow_recommend=False
    )
    assert "#" in with_recommend
    assert "#" not in without_recommend
    assert without_recommend.strip() == text
