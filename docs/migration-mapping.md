# 术语系统数据审计和迁移映射

## 审计日期
2026-04-14

## 数据统计

### 总体统计
- **总术语数**: 513
- **全局术语**: 94
- **项目术语**: 419
- **术语表文件数**: 17

### 项目分布（前9名）
1. clustermaxtm-2-0: 92 terms
2. inferencex-v2: 86 terms
3. apple-tsmc-partnership: 77 terms
4. rl-environments: 51 terms
5. claude-code: 25 terms
6. apple-tsmc: 24 terms
7. inferencemaxtm: 24 terms
8. memory-mania: 24 terms
9. dissecting-nvidia: 16 terms

### 策略分布
- translate: 275 (53.6%)
- preserve: 160 (31.2%)
- first_annotate: 72 (14.0%)
- preserve_annotate: 6 (1.2%)

### 来源分布
- term_review_auto: 251 (48.9%)
- unknown: 140 (27.3%)
- manual: 110 (21.4%)
- analysis_auto: 12 (2.3%)

### 状态分布
- active: 373 (72.7%)
- unknown: 140 (27.3%)

## 旧数据格式

### 旧术语格式（GlossaryTerm）
```json
{
  "original": "TSMC",
  "translation": "台积电",
  "strategy": "first_annotate",
  "note": "Taiwan Semiconductor Manufacturing Company",
  "tags": ["company"],
  "first_occurrence": null,
  "scope": "global",
  "source": "manual",
  "status": "active",
  "updated_at": "2026-03-12T12:47:53.570216"
}
```

### 字段说明
- `original`: 原文术语
- `translation`: 翻译（可为 null）
- `strategy`: 翻译策略（translate, preserve, first_annotate, preserve_annotate）
- `note`: 备注说明
- `tags`: 标签列表
- `first_occurrence`: 首次出现位置（通常为 null）
- `scope`: 作用域（global, project）
- `source`: 来源（manual, term_review_auto, analysis_auto）
- `status`: 状态（active, inactive）
- `updated_at`: 更新时间

## 新数据格式

### 新术语格式（Term + TermMetadata）

#### Term 模型
```python
Term(
    id="uuid-v5-generated",
    original="TSMC",
    translation="台积电",
    strategy="TRANSLATE",  # 映射后的策略
    source_lang="en",
    target_lang="zh"
)
```

#### TermMetadata 模型
```python
TermMetadata(
    term_id="uuid-v5-generated",
    scope="global",
    project_id=None,  # global 时为 None
    term_original="TSMC",
    term_translation="台积电",
    tags=["company"],
    source="manual",
    usage_count=0,
    is_deleted=False,  # status == "inactive" 时为 True
    created_at=datetime.now(),
    updated_at=datetime.fromisoformat("2026-03-12T12:47:53.570216")
)
```

## 字段映射

### 策略映射
| 旧策略 | 新策略 | 说明 |
|--------|--------|------|
| translate | TRANSLATE | 直接翻译 |
| preserve | KEEP | 保留原文 |
| first_annotate | TRANSLATE_ANNOTATE | 首次出现时注释 |
| preserve_annotate | KEEP_ANNOTATE | 保留原文并注释 |

### 状态映射
| 旧状态 | 新字段 | 值 |
|--------|--------|-----|
| active | is_deleted | False |
| inactive | is_deleted | True |
| unknown | is_deleted | False（默认） |

### 其他字段映射
| 旧字段 | 新位置 | 说明 |
|--------|--------|------|
| original | Term.original | 直接映射 |
| translation | Term.translation | 直接映射 |
| note | TermMetadata.notes | 存储在 metadata 中 |
| tags | TermMetadata.tags | 直接映射 |
| scope | TermMetadata.scope | 直接映射 |
| source | TermMetadata.source | 直接映射 |
| updated_at | TermMetadata.updated_at | 直接映射 |
| first_occurrence | - | 废弃（未使用） |

## UUID 生成策略

使用 UUID v5 确保确定性 ID 生成：

```python
import uuid

namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
term_id = uuid.uuid5(namespace, f"{scope}:{original}:{translation}")
```

这确保：
1. 相同的术语总是生成相同的 ID
2. 可以在不同环境中重现
3. 避免 ID 冲突

## 需要迁移的文件

### 数据文件
1. `glossary/global_glossary_semi.json` - 全局术语表
2. `projects/*/glossary.json` - 16个项目术语表

### 代码文件（需要清理）
1. `src/core/glossary.py` - 旧的 GlossaryManager
2. `src/core/glossary_prompt.py` - 旧的术语提示构建
3. `src/api/routers/glossary.py` - 旧的 API 路由
4. `src/api/routers/project_glossary.py` - 旧的项目术语 API
5. `src/api/utils/glossary.py` - 旧的工具函数
6. `src/cli/glossary.py` - 旧的 CLI 命令

## 迁移风险

### 高风险
1. **数据丢失**: 迁移过程中可能丢失数据
   - 缓解：完整备份 + dry-run 模式
2. **引用关系破坏**: 项目引用全局术语的关系可能丢失
   - 缓解：使用确定性 UUID + 验证脚本

### 中风险
1. **策略映射错误**: 旧策略到新策略的映射可能不准确
   - 缓解：详细的映射表 + 人工审核
2. **编码问题**: 中文字符可能出现编码问题
   - 缓解：统一使用 UTF-8

### 低风险
1. **性能问题**: 迁移可能耗时较长
   - 缓解：批量处理 + 进度显示

## 迁移步骤

1. **备份**: 备份所有术语数据文件
2. **Dry-run**: 运行迁移脚本的 dry-run 模式
3. **验证**: 检查 dry-run 结果
4. **执行**: 执行实际迁移
5. **验证**: 运行验证脚本
6. **测试**: 运行所有测试
7. **清理**: 清理旧代码（可选）

## 回滚计划

如果迁移失败：
1. 从备份恢复数据文件
2. 恢复旧代码（如果已删除）
3. 验证系统功能
4. 分析失败原因

## 成功标准

- ✅ 所有 513 个术语成功迁移
- ✅ 验证脚本 100% 通过
- ✅ 所有测试通过
- ✅ 备份文件完整
- ✅ 迁移报告详细
