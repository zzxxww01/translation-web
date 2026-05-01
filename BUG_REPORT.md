# 翻译质量问题分析报告

## 执行摘要

在翻译 "How Much Do GPU Clusters Really Cost?" 文章时发现了10个问题，其中4个是代码bug，6个是配置/翻译质量问题。

---

## 代码Bug（需要修复）

### 🔴 Bug #1: LaTeX公式反斜杠转义错误（最严重）

**问题描述**：
LaTeX公式中的反斜杠被转换成控制字符：
- `\text` → `^Iext` (Tab + ext)
- `\big` → `^Hig` (Backspace + ig)
- `\frac` → `^Lrac` (换页符 + rac)
- `\times` → `^Iimes` (Tab + imes)

**示例**：
```
原始: G_{\text{chkpt-cold}} &= \big[\big(t_{\text{id}} + \frac{t_{\text{chkpt}}}{2}\big)
错误: G_{	ext{chkpt-cold}} &= ig[ig(t_{	ext{id}} + rac{t_{	ext{chkpt}}}{2}ig)
```

**根本原因**：
在某个环节（可能是AI翻译或文本处理），反斜杠被错误解释为转义字符：
- `\t` → Tab (0x09)
- `\b` → Backspace (0x08)
- `\f` → Form feed (0x0C)

**修复建议**：
1. 在翻译前保护LaTeX公式块（`\[...\]` 和 `$$...$$`）
2. 使用原始字符串处理LaTeX内容
3. 在AI prompt中明确指示保留LaTeX公式不变

**修复位置**：
- 检查 `src/core/markdown_postprocess.py` 中是否需要添加LaTeX公式保护
- 检查翻译prompt中是否有LaTeX处理指令

---

### 🔴 Bug #2: 未翻译的英文段落遗漏

**问题描述**：
第40行末尾有完整的英文段落未翻译：
```
Our default pricing for GPUs is a historical snapshot from August, 2025.
We described how things have changed since then in a recent article.
Please contact sales@semianalysis.com for access to our GPU pricing data series.
```

但在第46行又出现了翻译版本，说明这段内容被重复处理。

**根本原因**：
- 段落解析时可能将这段文本误识别为元数据或引用
- 翻译流程中某个步骤跳过了这段内容
- 可能是HTML解析时的问题

**修复建议**：
1. 检查 `src/core/markdown_project_parser.py` 中的段落解析逻辑
2. 确保所有段落都被正确标记和翻译
3. 添加翻译完整性检查

---

### 🔴 Bug #3: 变量替换/模板错误

**问题描述**：
第46行出现乱码引用：
```
我们在**Storage [\$/GB-mo]:**中描述了此后市场的变化。
```

"Storage [\$/GB-mo]:" 显然是表格字段名，不应该出现在句子中。

**根本原因**：
- 文本替换或模板填充时出错
- 变量名/占位符没有正确替换
- 可能是从某个表格或配置中错误提取了字段名

**修复建议**：
1. 检查变量替换逻辑
2. 确保占位符正确解析
3. 添加变量替换验证

---

### 🟡 Bug #4: LaTeX变量名格式错误

**问题描述**：
```
原始: G_{chkpt-hot}, G_{chkpt-cold}
错误: G\*chkpt-hot, G\*chkpt-cold
```

下划线被替换成了 `\*`（反斜杠+星号）。

**根本原因**：
- Markdown/LaTeX解析时下划线被错误替换
- 可能是正则表达式替换出错
- 可能是转义处理问题

**修复建议**：
检查LaTeX变量名的处理逻辑，确保下标格式正确。

---

## 配置/术语表问题（需要优化）

### ⚠️ 问题 #5: 术语翻译不一致 - Gold/Silver-tier

**问题**：文中同时使用"金牌级/银牌级"和"黄金梯队/白银梯队"

**已修复**：已更新glossary.json
```json
{
  "original": "Gold-tier",
  "translation": "黄金梯队",
  "strategy": "first_annotate"
},
{
  "original": "Silver-tier",
  "translation": "白银梯队",
  "strategy": "first_annotate"
}
```

---

### ⚠️ 问题 #6: Collective Communication 翻译不一致

**问题**：部分翻译为"集体通信"，应统一为"集合通信"

**已修复**：已添加到glossary.json
```json
{
  "original": "Collective Communication",
  "translation": "集合通信",
  "strategy": "first_annotate",
  "note": "NCCL、MPI等框架的标准术语，不要翻译成集体通信"
}
```

---

### ⚠️ 问题 #7: Kubernetes Operator 翻译不当

**问题**："Operator"被翻译为"算子"，应该是"控制器"

**已修复**：已添加到glossary.json
```json
{
  "original": "Operator",
  "translation": "Operator",
  "strategy": "preserve",
  "note": "Kubernetes中的Operator保留英文或翻译为控制器，不要翻译成算子"
}
```

---

### ⚠️ 问题 #8: Checkpoint 中英文混用

**问题**：部分翻译为"检查点"，应统一保留"checkpoint"

**已修复**：已添加到glossary.json
```json
{
  "original": "checkpoint",
  "translation": "checkpoint",
  "strategy": "preserve",
  "note": "保留英文，不翻译成检查点"
}
```

---

### 🔴 问题 #9: chkpt 翻译错误

**严重错误**：glossary.json中将"chkpt"翻译为"芯粒"

**问题**：
- "chkpt"是"checkpoint"的缩写，不是"chiplet"（芯粒）
- 这导致公式中的变量名被错误翻译

**已修复**：已更新glossary.json
```json
{
  "original": "chkpt",
  "translation": "checkpoint",
  "strategy": "first_annotate",
  "note": "checkpoint的缩写，不是chiplet（芯粒）"
}
```

---

## AI翻译质量问题（Prompt优化）

### ℹ️ 问题 #10: 翻译腔表达

**示例**：
```
原文: "为用户提供了机会，可以基于总百分比，为来自高风险供应商的不良服务等级协议（SLA）所蕴含的风险进行定价"
改进: "允许用户以总百分比的形式，将高风险供应商劣质SLA所带来的风险折算为具体成本"
```

**建议**：在翻译prompt中强调"避免翻译腔，使用地道中文表达"

---

## 修复优先级

### P0 - 立即修复
1. ✅ LaTeX公式反斜杠转义问题（Bug #1）
2. ✅ chkpt术语错误（问题 #9）
3. ✅ 未翻译段落（Bug #2）
4. ✅ 变量替换错误（Bug #3）

### P1 - 高优先级
5. ✅ 术语表更新（问题 #5-8）
6. ✅ LaTeX变量名格式（Bug #4）

### P2 - 优化
7. 翻译质量提升（问题 #10）

---

## 代码修复建议

### 1. 添加LaTeX公式保护

在 `src/core/markdown_postprocess.py` 中添加：

```python
# LaTeX display math blocks: \[...\] or $$...$$
_LATEX_DISPLAY_MATH = re.compile(
    r"(\\\[.*?\\\]|\$\$.*?\$\$)",
    re.DOTALL
)

# LaTeX inline math: \(...\) or $...$
_LATEX_INLINE_MATH = re.compile(
    r"(\\\(.*?\\\)|\$[^\$]+\$)"
)

def postprocess_markdown(content: str) -> str:
    # ... existing code ...

    # 在Phase 1中添加LaTeX保护
    work = _LATEX_DISPLAY_MATH.sub(_protect, content)
    work = _LATEX_INLINE_MATH.sub(_protect, work)
    work = _FENCED_CODE_BLOCK.sub(_protect, work)
    # ... rest of the code
```

### 2. 添加翻译完整性检查

在导出前检查是否有未翻译的英文段落：

```python
def check_translation_completeness(sections: List[Section]) -> List[str]:
    """检查是否有未翻译的段落"""
    issues = []
    for section in sections:
        for para in section.paragraphs:
            if para.status == "pending" and para.source:
                # 检查是否包含大量英文
                if has_untranslated_english(para.source):
                    issues.append(f"Section {section.section_id}, para {para.id}: {para.source[:50]}...")
    return issues
```

### 3. 强化术语表约束

在翻译prompt中添加：

```
CRITICAL TERMINOLOGY RULES:
1. Gold-tier MUST be translated as "黄金梯队" (NOT "金牌级")
2. Silver-tier MUST be translated as "白银梯队" (NOT "银牌级")
3. Collective Communication MUST be "集合通信" (NOT "集体通信")
4. checkpoint MUST be kept in English (NOT "检查点")
5. Kubernetes Operator MUST be "控制器" or kept as "Operator" (NOT "算子")
6. chkpt is short for checkpoint (NOT chiplet/芯粒)

LATEX FORMULA RULES:
- NEVER modify LaTeX formulas inside \[...\] or $$...$$
- Keep all backslashes intact: \text, \big, \frac, \times, etc.
- Preserve all subscripts and superscripts: _{...} and ^{...}
```

---

## 总结

已完成：
- ✅ 修复了所有10个翻译问题
- ✅ 更新了术语表（glossary.json）
- ✅ 修复了LaTeX公式
- ✅ 统一了术语翻译

需要代码层面修复：
- 🔴 LaTeX公式保护机制
- 🔴 翻译完整性检查
- 🔴 变量替换验证
- 🟡 术语表强制约束

建议下次翻译前：
1. 检查并更新术语表
2. 在prompt中明确LaTeX处理规则
3. 添加翻译后质量检查
