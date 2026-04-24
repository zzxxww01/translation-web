#!/usr/bin/env python3
"""
测试质量报告生成器
对已翻译的 CPO 项目生成质量报告
"""

import sys
import json
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.quality_report_generator import QualityReportGenerator
from src.core.project import ProjectManager
from src.llm.gemini import GeminiProvider


async def test_quality_report():
    """测试质量报告生成"""

    project_id = "co-packaged-optics-cpo"

    print(f"=" * 60)
    print(f"测试质量报告生成器")
    print(f"项目: {project_id}")
    print(f"=" * 60)

    # 1. 加载项目
    print("\n[1/4] 加载项目...")
    project_manager = ProjectManager()
    project = project_manager.get(project_id)

    if not project:
        print(f"❌ 项目不存在: {project_id}")
        return False

    # 加载所有章节
    sections = project_manager.get_sections(project_id)

    print(f"✓ 项目加载成功")
    print(f"  - 章节数: {len(sections)}")
    print(f"  - 总段落数: {sum(len(s.paragraphs) for s in sections)}")

    # 2. 收集译文
    print("\n[2/4] 收集译文...")
    translations = {}
    total_translated = 0

    for section in sections:
        section_translations = []
        for para in section.paragraphs:
            translation = para.best_translation_text()
            if translation:
                section_translations.append(translation)
                total_translated += 1
            else:
                section_translations.append("")

        if section_translations:
            translations[section.section_id] = section_translations

    print(f"✓ 译文收集完成")
    print(f"  - 已翻译段落: {total_translated}")
    print(f"  - 章节数: {len(translations)}")

    if total_translated == 0:
        print("❌ 没有找到已翻译的内容")
        return False

    # 3. 创建 Gemini Provider
    print("\n[3/4] 初始化 Gemini Preview...")
    try:
        llm_provider = GeminiProvider(model="preview")
        print(f"✓ Gemini Preview 初始化成功")
    except Exception as e:
        print(f"❌ Gemini Provider 初始化失败: {e}")
        return False

    # 4. 生成质量报告
    print("\n[4/4] 生成质量报告...")
    generator = QualityReportGenerator(llm_provider)

    try:
        report = generator.generate_report(
            sections=sections,
            translations=translations,
            article_analysis=None
        )

        print(f"\n{'=' * 60}")
        print(f"质量报告生成成功！")
        print(f"{'=' * 60}")

        # 打印摘要
        print(f"\n📊 质量摘要:")
        print(f"  - 总问题数: {report.summary.total_issues}")
        print(f"  - 术语问题: {report.summary.terminology_issues}")
        print(f"  - 逻辑问题: {report.summary.logic_issues}")
        print(f"  - 流畅性问题: {report.summary.fluency_issues}")
        print(f"  - 整体质量: {report.summary.overall_quality}")
        print(f"  - 整体评分: {report.summary.overall_score}/10")

        print(f"\n📈 严重程度分布:")
        print(f"  - 高: {report.summary.high_severity_count}")
        print(f"  - 中: {report.summary.medium_severity_count}")
        print(f"  - 低: {report.summary.low_severity_count}")

        # 打印前 5 个问题
        if report.issues:
            print(f"\n🔍 问题示例 (前5个):")
            for i, issue in enumerate(report.issues[:5], 1):
                print(f"\n  [{i}] {issue.type.upper()} - {issue.severity.upper()}")
                print(f"      描述: {issue.description}")
                print(f"      问题句: {issue.problematic_sentence[:60]}...")
                print(f"      建议: {issue.suggestion[:80]}...")
                print(f"      位置: {issue.section_id}:{issue.paragraph_index}:{issue.sentence_index}")
                print(f"      置信度: {issue.match_confidence:.2f}")

        # 保存报告
        output_path = Path(f"projects/{project_id}/artifacts/quality_report_test.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

        print(f"\n💾 报告已保存到: {output_path}")

        return True

    except Exception as e:
        print(f"❌ 质量报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_quality_report())
    sys.exit(0 if success else 1)
