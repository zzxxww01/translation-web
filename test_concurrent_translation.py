#!/usr/bin/env python3
"""
并发全文翻译追踪测试
使用 BatchTranslationService 实现10个章节并发翻译
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from src.api.utils.llm_factory import create_llm_provider
from src.core.project import ProjectManager
from src.services.batch_translation_service import BatchTranslationService
from src.services.batch_translation_types import TranslationProgress

# 加载环境变量
load_dotenv()

# 项目配置
PROJECT_ID = "co-packaged-optics-cpo"
TRACE_DIR = Path(__file__).parent / "cpo-translation-trace"
TRACE_DIR.mkdir(exist_ok=True)

class ConcurrentTranslationTracer:
    """并发翻译追踪器"""

    def __init__(self):
        self.project_id = PROJECT_ID
        self.pm = ProjectManager()

        # 使用grok模型做翻译和分析
        self.llm = create_llm_provider("grok-4-20-non-reasoning")
        self.analysis_llm = create_llm_provider("grok-4-20-non-reasoning")

        print(f"✓ 翻译模型: {type(self.llm).__name__}")
        print(f"✓ 分析模型: {type(self.analysis_llm).__name__}")

        # 创建批量翻译服务（10个章节并发）
        self.batch_service = BatchTranslationService(
            llm_provider=self.llm,
            project_manager=self.pm,
            translation_mode=BatchTranslationService.TRANSLATION_MODE_FOUR_STEP,
            max_concurrent_sections=10,
            analysis_llm_provider=self.analysis_llm,  # 使用deepseek做分析
        )

        print(f"✓ BatchTranslationService 创建成功")
        print(f"  translation_llm: {type(self.batch_service.llm).__name__}")
        print(f"  analysis_llm: {type(self.batch_service.analysis_llm).__name__}")

        # 追踪日志
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = TRACE_DIR / f"concurrent_trace_{timestamp}.jsonl"
        self.report_file = TRACE_DIR / f"concurrent_report_{timestamp}.md"
        self.start_time = time.time()

        # 统计数据
        self.stats = {
            "total_sections": 0,
            "total_paragraphs": 0,
            "translated_paragraphs": 0,
            "skipped_paragraphs": 0,
            "error_paragraphs": 0,
            "section_times": [],
            "paragraph_times": [],
        }

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """记录事件到JSONL"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "elapsed": time.time() - self.start_time,
            "type": event_type,
            **data
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def on_progress(self, step_name: str, current: int, total: int):
        """进度回调"""
        self.log_event("progress", {
            "step_name": step_name,
            "current": current,
            "total": total,
        })

        # 打印进度
        print(f"[进度] {step_name}: {current}/{total}")

    async def on_term_conflict(self, conflict):
        """术语冲突回调"""
        self.log_event("term_conflict", {
            "term": conflict.term,
            "existing": conflict.existing_translation,
            "suggested": conflict.suggested_translation,
        })
        print(f"[术语冲突] {conflict.term}: {conflict.existing_translation} vs {conflict.suggested_translation}")
        return None  # 保持现有翻译

    async def run_translation(self):
        """运行并发翻译"""
        print(f"开始并发翻译测试 - 项目: {self.project_id}")
        print(f"使用模型: vectorengine/doubao-seed-2-0-lite-260215")
        print(f"并发度: {self.batch_service.max_concurrent_sections} 个章节")
        print(f"追踪日志: {self.log_file}")
        print("-" * 80)

        # 加载项目
        project = self.pm.get(self.project_id)
        sections = self.pm.get_sections(self.project_id)

        self.stats["total_sections"] = len(sections)
        self.stats["total_paragraphs"] = sum(len(s.paragraphs) for s in sections)

        print(f"项目加载完成: {len(sections)} 个章节, {self.stats['total_paragraphs']} 个段落")

        self.log_event("translation_start", {
            "project_id": self.project_id,
            "total_sections": self.stats["total_sections"],
            "total_paragraphs": self.stats["total_paragraphs"],
            "concurrent_sections": self.batch_service.max_concurrent_sections,
        })

        try:
            # 运行批量翻译
            result = await self.batch_service.translate_project(
                self.project_id,
                on_progress=self.on_progress,
                on_term_conflict=self.on_term_conflict,
            )

            elapsed = time.time() - self.start_time

            self.log_event("translation_complete", {
                "elapsed": elapsed,
                "result": result,
                "stats": self.stats,
            })

            print("-" * 80)
            print(f"翻译完成! 总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
            print(f"已翻译: {self.stats['translated_paragraphs']} 个段落")
            print(f"已跳过: {self.stats['skipped_paragraphs']} 个段落")
            print(f"错误: {self.stats['error_paragraphs']} 个段落")

            # 生成报告
            self.generate_report(result, elapsed)

        except Exception as e:
            self.log_event("translation_error", {
                "error": str(e),
                "error_type": type(e).__name__,
            })
            print(f"翻译失败: {e}")
            raise

    def generate_report(self, result: Dict[str, Any], elapsed: float):
        """生成分析报告"""
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write(f"# 并发翻译追踪报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write(f"## 基本信息\n\n")
            f.write(f"- 项目ID: {self.project_id}\n")
            f.write(f"- 使用模型: vectorengine/doubao-seed-2-0-lite-260215\n")
            f.write(f"- 并发度: {self.batch_service.max_concurrent_sections} 个章节\n")
            f.write(f"- 总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)\n\n")

            f.write(f"## 翻译统计\n\n")
            f.write(f"- 总章节数: {self.stats['total_sections']}\n")
            f.write(f"- 总段落数: {self.stats['total_paragraphs']}\n")
            f.write(f"- 已翻译: {self.stats['translated_paragraphs']}\n")
            f.write(f"- 已跳过: {self.stats['skipped_paragraphs']}\n")
            f.write(f"- 错误: {self.stats['error_paragraphs']}\n\n")

            if self.stats['translated_paragraphs'] > 0:
                avg_time = elapsed / self.stats['translated_paragraphs']
                f.write(f"- 平均翻译速度: {avg_time:.1f}秒/段落\n\n")

            f.write(f"## 详细结果\n\n")
            f.write(f"```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```\n\n")

            f.write(f"## 追踪日志\n\n")
            f.write(f"详细追踪日志: {self.log_file}\n")

        print(f"分析报告已生成: {self.report_file}")

async def main():
    """主函数"""
    tracer = ConcurrentTranslationTracer()
    await tracer.run_translation()

if __name__ == "__main__":
    asyncio.run(main())
