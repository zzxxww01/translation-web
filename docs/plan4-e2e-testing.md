# Plan 4 端到端测试指南

## 概述

本文档描述如何对 Plan 4（翻译会话管理）进行端到端测试，验证术语系统与四步翻译法的完整集成。

## 测试场景

### 场景 1: 基本翻译流程（带术语管理）

**目标**: 验证翻译会话的完整生命周期

**步骤**:
1. 准备测试数据
   - 创建项目目录
   - 添加术语到术语库（全局和项目级别）
   - 准备源文档

2. 初始化翻译器
```python
from src.agents.four_step_translator import FourStepTranslator
from src.agents.context_manager import LayeredContextManager
from src.services.translation_session_service import TranslationSessionService
from src.services.term_injection_service import TermInjectionService
from src.services.term_validation_service import TermValidationService
from src.services.glossary_storage import GlossaryStorage

# 创建服务
storage = GlossaryStorage("path/to/glossary")
session_service = TranslationSessionService("path/to/sessions")
injection_service = TermInjectionService()
validation_service = TermValidationService()

# 创建翻译器
translator = FourStepTranslator(
    llm_provider=llm,
    context_manager=context_manager,
    session_service=session_service,
    term_injection_service=injection_service,
    term_validation_service=validation_service
)
```

3. 执行翻译
```python
result = translator.translate_section(
    section=section,
    all_sections=all_sections,
    project_id="test-project"
)
```

4. 验证结果
   - 检查会话已创建
   - 检查会话状态为 "completed"
   - 检查术语快照已保存
   - 检查翻译结果包含正确的术语翻译
   - 检查验证报告（如果有违规）

**预期结果**:
- 会话成功创建并完成
- 术语正确应用到翻译中
- 验证报告显示无违规或仅有非严格违规

### 场景 2: 术语验证失败

**目标**: 验证术语验证能够检测到违规

**步骤**:
1. 准备包含特定术语的源文本
2. 添加术语到术语库（TRANSLATE 策略）
3. Mock LLM 返回不包含术语翻译的结果
4. 执行翻译
5. 检查验证报告

**预期结果**:
- 验证报告包含 MISSING_TRANSLATION 违规
- 日志中有警告信息

### 场景 3: 向后兼容性

**目标**: 验证不使用术语服务时翻译器仍能正常工作

**步骤**:
1. 创建翻译器，不传入术语服务
```python
translator = FourStepTranslator(
    llm_provider=llm,
    context_manager=context_manager
)
```

2. 执行翻译
3. 验证结果

**预期结果**:
- 翻译正常完成
- 不创建会话
- 不进行术语验证

### 场景 4: 会话失败处理

**目标**: 验证翻译失败时会话状态正确更新

**步骤**:
1. Mock LLM 抛出异常
2. 执行翻译（捕获异常）
3. 检查会话状态

**预期结果**:
- 会话状态为 "failed"
- 错误信息已记录

## 单元测试覆盖

已完成的单元测试：

### TranslationSessionService (16 tests)
- ✅ 会话创建
- ✅ 会话状态更新
- ✅ 会话暂停/恢复
- ✅ 会话完成
- ✅ 会话失败
- ✅ 术语快照管理

### TermInjectionService (15 tests)
- ✅ 约束构建
- ✅ 术语使用跟踪
- ✅ 首次出现标记
- ✅ 多种翻译策略

### TermValidationService (14 tests)
- ✅ 翻译验证
- ✅ 违规检测
- ✅ 批量验证
- ✅ 严格/非严格模式

### FourStepTranslator Integration (5 tests)
- ✅ 服务注入
- ✅ 向后兼容性
- ✅ 术语表上下文构建

**总计**: 50 个单元测试，全部通过

## 集成测试状态

由于项目的复杂依赖关系（LLM、存储、模型等），完整的端到端集成测试需要：

1. **Mock 策略**: 使用 Mock 对象模拟所有外部依赖
2. **测试环境**: 设置临时文件系统和数据库
3. **测试数据**: 准备真实的术语和文档样本

建议在实际项目中运行手动端到端测试，使用真实的 LLM 和数据。

## 手动测试清单

- [ ] 创建测试项目
- [ ] 添加全局术语（5-10个）
- [ ] 添加项目术语（5-10个）
- [ ] 准备包含这些术语的源文档
- [ ] 运行翻译
- [ ] 检查会话文件
- [ ] 检查术语快照
- [ ] 检查翻译结果
- [ ] 检查验证报告
- [ ] 测试暂停/恢复功能
- [ ] 测试错误处理

## 性能测试

建议的性能指标：

- 会话创建: < 100ms
- 术语注入: < 50ms
- 术语验证: < 200ms（取决于术语数量）
- 总体开销: < 5% 的翻译时间

## 已知限制

1. 术语注入服务目前使用旧的术语格式（EnhancedTerm），未来需要迁移到新的 Term 模型
2. 验证服务在非严格模式下总是返回 is_valid=True，即使有违规
3. 会话服务不支持分布式环境（文件系统存储）

## 下一步

1. 完成 Plan 5（数据迁移）
2. 将旧术语系统数据迁移到新系统
3. 更新术语注入逻辑以使用新的 Term 模型
4. 添加更多集成测试场景
