#!/usr/bin/env python3
"""
完整全文翻译追踪测试
模拟点击"全文一键翻译"按钮，追踪整个链路的每一步
重点：排查效果、不符合预期的点、待改进的问题
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.project import ProjectManager
from src.core.glossary import GlossaryManager
from src.agents.translation import TranslationAgent, TranslationContext, apply_translation_payload
from src.api.utils.llm_factory import create_llm_provider
from src.config.timeout_config import TimeoutConfig
from src.core.structured_metadata import is_structured_metadata_paragraph

PROJECT_ID = "co-packaged-optics-cpo"
TRACE_DIR = Path(__file__).parent / "translation-agent-analysis" / "cpo-translation-trace" / "traces"
TRACE_DIR.mkdir(parents=True, exist_ok=True)

def _build_translation_context(section, paragraph_index, glossary):
    """构建翻译上下文"""
    # 构建previous_paragraphs列表（最近3个已翻译段落）
    previous_paragraphs = []
    for i in range(max(0, paragraph_index - 3), paragraph_index):
        p = section.paragraphs[i]
        if p.source:
            # 获取最新翻译
            trans_text = p.latest_translation_text(non_empty=True)
            if trans_text:
                previous_paragraphs.append((p.source, trans_text))

    # 构建next_preview列表（接下来2个段落的原文）
    next_preview = []
    for i in range(paragraph_index + 1, min(len(section.paragraphs), paragraph_index + 3)):
        p = section.paragraphs[i]
        if p.source:
            next_preview.append(p.source)

    return TranslationContext(
        glossary=glossary,
        current_section_title=section.title or "",
        previous_paragraphs=previous_paragraphs,
        next_preview=next_preview,
    )

class FullTranslationTracer:
    """全文翻译追踪器"""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.pm = ProjectManager()
        self.gm = GlossaryManager()
        # 明确指定使用豆包模型（通过vectorengine provider）
        self.llm = create_llm_provider(provider="vectorengine", model="doubao-seed-2-0-lite-260215")

        timeout_s = TimeoutConfig.get_timeout("longform")
        self.agent = TranslationAgent(self.llm, timeout=timeout_s)

        self.stats = {
            "total_paragraphs": 0,
            "skipped_metadata": 0,
            "skipped_translated": 0,
            "translated": 0,
            "errors": 0,
            "error_details": [],
            "section_stats": [],
            "timing": {},
            "quality_issues": [],  # 质量问题
            "unexpected_behaviors": [],  # 不符合预期的行为
        }

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.trace_file = TRACE_DIR / f"full_translation_{timestamp}.jsonl"
        self.report_file = TRACE_DIR / f"full_translation_report_{timestamp}.md"

    def log_event(self, event_type: str, data: dict):
        """记录事件到JSONL"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            **data
        }
        with open(self.trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def analyze_translation_quality(self, paragraph, payload, context):
        """分析翻译质量，发现问题"""
        issues = []

        # 检查1: 翻译是否为空
        if not payload.text or not payload.text.strip():
            issues.append({
                "type": "empty_translation",
                "severity": "critical",
                "paragraph_id": paragraph.id,
                "source_length": len(paragraph.source),
            })

        # 检查2: 翻译长度异常（过短或过长）
        source_len = len(paragraph.source)
        trans_len = len(payload.text) if payload.text else 0
        ratio = trans_len / source_len if source_len > 0 else 0

        if ratio < 0.2:
            issues.append({
                "type": "translation_too_short",
                "severity": "high",
                "paragraph_id": paragraph.id,
                "ratio": ratio,
                "source_length": source_len,
                "translation_length": trans_len,
            })
        elif ratio > 3.0:
            issues.append({
                "type": "translation_too_long",
                "severity": "medium",
                "paragraph_id": paragraph.id,
                "ratio": ratio,
                "source_length": source_len,
                "translation_length": trans_len,
            })

        # 检查3: 是否包含原文（可能是翻译失败）
        if paragraph.source[:50] in (payload.text or ""):
            issues.append({
                "type": "contains_source_text",
                "severity": "high",
                "paragraph_id": paragraph.id,
                "description": "译文中包含原文，可能翻译失败",
            })

        # 检查4: 术语表使用情况
        if context.glossary:
            used_terms = []
            missed_terms = []
            for term_entry in context.glossary.terms:
                term = term_entry.original
                translation = term_entry.translation

                if term and translation and term in paragraph.source:
                    if translation in (payload.text or ""):
                        used_terms.append(term)
                    else:
                        missed_terms.append({
                            "term": term,
                            "expected": translation,
                        })

            if missed_terms:
                issues.append({
                    "type": "glossary_terms_missed",
                    "severity": "medium",
                    "paragraph_id": paragraph.id,
                    "missed_count": len(missed_terms),
                    "missed_terms": missed_terms[:5],  # 只记录前5个
                })

        return issues

    def run_full_translation(self, max_paragraphs: int = None):
        """运行完整翻译流程"""
        print(f"🚀 开始全文翻译追踪: {self.project_id}")
        print(f"📝 追踪日志: {self.trace_file}")
        print(f"📊 分析报告: {self.report_file}")
        print()

        start_time = datetime.now()
        self.log_event("translation_start", {"project_id": self.project_id})

        # 加载章节和术语表
        sections = self.pm.get_sections(self.project_id)
        glossary = self.gm.load_merged(self.project_id)

        self.log_event("loaded_resources", {
            "sections_count": len(sections),
            "glossary_terms": len(glossary.terms) if glossary and hasattr(glossary, 'terms') else 0,
        })

        print(f"📚 加载了 {len(sections)} 个章节")
        print(f"📖 术语表包含 {len(glossary.terms) if glossary and hasattr(glossary, 'terms') else 0} 个术语")
        print()

        # 统计总段落数
        self.stats["total_paragraphs"] = sum(len(s.paragraphs) for s in sections)
        processed = 0

        # 遍历所有章节
        for section_idx, section in enumerate(sections):
            section_start = datetime.now()
            section_full = self.pm.get_section(self.project_id, section.section_id)

            if not section_full:
                continue

            section_stats = {
                "section_id": section.section_id,
                "title": section.title,
                "total_paragraphs": len(section_full.paragraphs),
                "translated": 0,
                "skipped": 0,
                "errors": 0,
            }

            print(f"📄 [{section_idx+1}/{len(sections)}] {section.title or section.section_id}")

            # 遍历段落
            for para_idx, paragraph in enumerate(section_full.paragraphs):
                processed += 1

                # 检查是否达到限制
                if max_paragraphs and processed > max_paragraphs:
                    print(f"\n⚠️  达到测试限制 ({max_paragraphs} 段落)，停止翻译")
                    break

                # 跳过元数据段落
                if is_structured_metadata_paragraph(paragraph):
                    self.stats["skipped_metadata"] += 1
                    section_stats["skipped"] += 1
                    self.log_event("skip_metadata", {
                        "paragraph_id": paragraph.id,
                        "section_id": section.section_id,
                    })
                    continue

                # 跳过已翻译段落
                if paragraph.has_usable_translation():
                    self.stats["skipped_translated"] += 1
                    section_stats["skipped"] += 1
                    self.log_event("skip_translated", {
                        "paragraph_id": paragraph.id,
                        "section_id": section.section_id,
                    })
                    continue

                # 构建上下文
                context = _build_translation_context(section_full, para_idx, glossary)

                # 翻译段落
                para_start = datetime.now()
                try:
                    print(f"  [{para_idx+1}/{len(section_full.paragraphs)}] 翻译中...", end="", flush=True)

                    payload = self.agent.translate_paragraph(paragraph, context)

                    para_duration = (datetime.now() - para_start).total_seconds()

                    # 质量分析
                    quality_issues = self.analyze_translation_quality(paragraph, payload, context)
                    if quality_issues:
                        self.stats["quality_issues"].extend(quality_issues)

                    # 应用翻译
                    apply_translation_payload(paragraph, payload, "default")
                    self.pm.save_section(self.project_id, section_full)

                    self.stats["translated"] += 1
                    section_stats["translated"] += 1

                    self.log_event("paragraph_translated", {
                        "paragraph_id": paragraph.id,
                        "section_id": section.section_id,
                        "source_length": len(paragraph.source),
                        "translation_length": len(payload.text) if payload.text else 0,
                        "duration_seconds": para_duration,
                        "quality_issues": quality_issues,
                    })

                    print(f" ✓ ({para_duration:.1f}s)")

                except Exception as e:
                    para_duration = (datetime.now() - para_start).total_seconds()
                    self.stats["errors"] += 1
                    section_stats["errors"] += 1

                    error_detail = {
                        "paragraph_id": paragraph.id,
                        "section_id": section.section_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "duration_seconds": para_duration,
                    }
                    self.stats["error_details"].append(error_detail)

                    self.log_event("paragraph_error", error_detail)

                    print(f" ✗ {type(e).__name__}: {str(e)[:50]}")

            section_duration = (datetime.now() - section_start).total_seconds()
            section_stats["duration_seconds"] = section_duration
            self.stats["section_stats"].append(section_stats)

            print(f"  ✓ 章节完成: 翻译 {section_stats['translated']}, 跳过 {section_stats['skipped']}, 错误 {section_stats['errors']}")
            print()

            if max_paragraphs and processed > max_paragraphs:
                break

        total_duration = (datetime.now() - start_time).total_seconds()
        self.stats["timing"]["total_seconds"] = total_duration

        self.log_event("translation_complete", self.stats)

        # 生成报告
        self.generate_report()

        print(f"\n✅ 翻译完成!")
        print(f"📊 总耗时: {total_duration:.1f}s")
        print(f"📝 已翻译: {self.stats['translated']}/{self.stats['total_paragraphs']}")
        print(f"⚠️  错误: {self.stats['errors']}")
        print(f"🔍 质量问题: {len(self.stats['quality_issues'])}")
        print(f"\n📄 详细报告: {self.report_file}")

    def generate_report(self):
        """生成详细分析报告"""
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write("# 全文翻译完整链路追踪报告\n\n")
            f.write(f"**项目**: {self.project_id}\n")
            f.write(f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**追踪日志**: {self.trace_file.name}\n\n")

            f.write("## 📊 整体统计\n\n")
            f.write(f"- 总段落数: {self.stats['total_paragraphs']}\n")
            f.write(f"- 已翻译: {self.stats['translated']}\n")
            f.write(f"- 跳过（元数据）: {self.stats['skipped_metadata']}\n")
            f.write(f"- 跳过（已翻译）: {self.stats['skipped_translated']}\n")
            f.write(f"- 错误: {self.stats['errors']}\n")
            f.write(f"- 总耗时: {self.stats['timing'].get('total_seconds', 0):.1f}秒\n\n")

            if self.stats['translated'] > 0:
                avg_time = self.stats['timing'].get('total_seconds', 0) / self.stats['translated']
                f.write(f"- 平均翻译速度: {avg_time:.2f}秒/段落\n\n")

            # 质量问题汇总
            f.write("## 🔍 质量问题分析\n\n")
            if self.stats['quality_issues']:
                issue_types = {}
                for issue in self.stats['quality_issues']:
                    issue_type = issue['type']
                    if issue_type not in issue_types:
                        issue_types[issue_type] = []
                    issue_types[issue_type].append(issue)

                f.write(f"发现 {len(self.stats['quality_issues'])} 个质量问题:\n\n")
                for issue_type, issues in sorted(issue_types.items(), key=lambda x: len(x[1]), reverse=True):
                    f.write(f"### {issue_type} ({len(issues)}个)\n\n")
                    for issue in issues[:5]:  # 只显示前5个
                        f.write(f"- 段落: {issue.get('paragraph_id', 'N/A')}\n")
                        f.write(f"  - 严重程度: {issue.get('severity', 'unknown')}\n")
                        for key, value in issue.items():
                            if key not in ['type', 'severity', 'paragraph_id']:
                                f.write(f"  - {key}: {value}\n")
                        f.write("\n")
            else:
                f.write("✅ 未发现明显质量问题\n\n")

            # 错误详情
            if self.stats['error_details']:
                f.write("## ❌ 错误详情\n\n")
                for error in self.stats['error_details']:
                    f.write(f"### 段落 {error['paragraph_id']}\n")
                    f.write(f"- 章节: {error['section_id']}\n")
                    f.write(f"- 错误类型: {error['error_type']}\n")
                    f.write(f"- 错误信息: {error['error']}\n")
                    f.write(f"- 耗时: {error['duration_seconds']:.2f}秒\n\n")

            # 章节统计
            f.write("## 📚 章节统计\n\n")
            f.write("| 章节 | 总段落 | 已翻译 | 跳过 | 错误 | 耗时(s) |\n")
            f.write("|------|--------|--------|------|------|--------|\n")
            for section in self.stats['section_stats']:
                f.write(f"| {section['title'][:30]} | {section['total_paragraphs']} | "
                       f"{section['translated']} | {section['skipped']} | "
                       f"{section['errors']} | {section.get('duration_seconds', 0):.1f} |\n")

            f.write("\n## 🎯 改进建议\n\n")

            # 基于发现的问题给出建议
            if any(issue['type'] == 'translation_too_short' for issue in self.stats['quality_issues']):
                f.write("- ⚠️ 发现多个翻译过短的情况，建议检查模型是否正确理解了翻译任务\n")

            if any(issue['type'] == 'glossary_terms_missed' for issue in self.stats['quality_issues']):
                f.write("- ⚠️ 术语表中的术语未被正确使用，建议优化术语表注入方式\n")

            if self.stats['errors'] > 0:
                f.write(f"- ⚠️ 发现 {self.stats['errors']} 个翻译错误，建议添加重试机制\n")

            if self.stats['translated'] > 0:
                avg_time = self.stats['timing'].get('total_seconds', 0) / self.stats['translated']
                if avg_time > 30:
                    f.write(f"- ⚠️ 平均翻译速度较慢 ({avg_time:.1f}s/段落)，建议考虑并行化或使用更快的模型\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="全文翻译完整链路追踪")
    parser.add_argument("--max-paragraphs", type=int, help="限制翻译段落数（用于测试）")
    args = parser.parse_args()

    tracer = FullTranslationTracer(PROJECT_ID)
    tracer.run_full_translation(max_paragraphs=args.max_paragraphs)
