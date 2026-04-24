#!/bin/bash
# 清理中间文件脚本
# 保留：最终测试报告 + 四阶段集成测试代码

echo "开始清理中间文件..."

# 删除中间分析脚本
echo "删除中间分析脚本..."
rm -f analyze_problems_2_4.py
rm -f analyze_term_extraction.py
rm -f calculate_multi_round_cost.py
rm -f generate_phase0_report.py
rm -f rethink_term_extraction.py
rm -f solution_5_combined_approach.py
rm -f solution_5_complete_workflow.py
rm -f solution_5_llm_calls.py
rm -f solution_6_combined_approach.py

# 删除临时测试脚本（保留 test_quality_report.py 作为 Phase 3 测试）
echo "删除临时测试脚本..."
rm -f test_concurrent_simple.py
rm -f test_japanese_debug.py
rm -f test_japanese_translation.py
rm -f test_vectorengine_speed.py

# 删除监控脚本
echo "删除监控脚本..."
rm -f check_progress.sh
rm -f monitor_four_steps.sh
rm -f monitor_translation.sh
rm -f watch_four_steps.sh

# 删除临时输出文件
echo "删除临时输出文件..."
rm -f detailed_phase2_report.txt
rm -f phase2_report_output.txt
rm -f test_solution6_simple_output.txt
rm -f IMPLEMENTATION_PLAN_SOLUTION_6.md

# 删除临时目录
echo "删除临时目录..."
rm -rf cpo-translation-trace/
rm -rf test_prompts/
rm -rf test_results/
rm -rf translation-agent-analysis/

# 删除中间文档（保留最终报告）
echo "删除中间文档..."
cd docs/

# Phase 0: 保留最终推荐，删除对比分析
rm -f PHASE0_模型对比分析.md

# Phase 2: 保留最终优化实施报告和方案C端到端测试报告，删除其他中间文档
rm -f PHASE2_SCORE_分析与优化建议.md
rm -f PHASE2_优化方案_合并Step4和Step5.md
rm -f PHASE2_完整执行报告.md
rm -f PHASE2_完整逻辑与优化总结.md
rm -f PHASE2_方案C_完整设计.md
rm -f PHASE2_深度分析报告.md
rm -f PHASE2_精修阶段分析与优化.md

# 删除其他临时文档
rm -f phase-based-model-selection.md
rm -f phase1-status-and-optimization.md

cd ..

echo "清理完成！"
echo ""
echo "保留的文件："
echo "  测试代码："
echo "    - test_concurrent_translation.py (Phase 0 并发测试)"
echo "    - test_full_translation_trace.py (四阶段集成测试)"
echo "    - test_quality_report.py (Phase 3 质量报告测试)"
echo ""
echo "  文档："
echo "    - docs/CPO文章API调用分析.md"
echo "    - docs/PHASE0_最终推荐.md"
echo "    - docs/PHASE1_模型评估与性能分析.md"
echo "    - docs/PHASE2_优化实施报告.md"
echo "    - docs/PHASE2_方案C_端到端测试报告.md"
echo "    - docs/PHASE3_最终审校机制分析.md"
echo "    - docs/PHASE3_质量报告生成器_设计方案.md"
echo "    - docs/长文翻译链路.md"
echo "    - docs/完整翻译链路总结.md"
