# Plan 2: 术语匹配引擎

## 概述

实现高精度的术语匹配引擎，支持多种术语类型的智能识别和验证。

**目标**：
- 实现术语分类器（TermClassifier）
- 实现模式编译器（PatternCompiler）
- 实现匹配验证器（MatchValidator）
- 实现统一匹配接口（TermMatcher）
- 达到 95%+ 的匹配准确率

**预计时间**：1.5-2 周

---

## 任务清单

### Task 2.1: 实现术语分类器

**目标**：根据术语特征自动分类

**文件**：`src/services/term_matcher/classifier.py`

**术语类型定义**：

```python
from enum import Enum

class TermType(str, Enum):
    """术语类型"""
    SHORT_ACRONYM = "short_acronym"      # 2-4字符缩写：AI, HBM, GPU
    MIXED_CASE = "mixed_case"            # 驼峰/混合大小写：CoWoS, HBM3E, iPhone
    COMMON_WORD = "common_word"          # 普通词：memory, chip, process
    SPECIAL_CHAR = "special_char"        # 包含特殊字符：C++, .NET, 3D-IC
    CHINESE = "chinese"                  # 中文术语：芯片、内存

class TermClassifier:
    """术语分类器"""
    
    @staticmethod
    def classify(term: str) -> TermType:
        """分类术语"""
        # 1. 检测中文
        if re.search(r'[\u4e00-\u9fff]', term):
            return TermType.CHINESE
        
        # 2. 检测特殊字符
        if re.search(r'[+\-./]', term):
            return TermType.SPECIAL_CHAR
        
        # 3. 检测短缩写（2-4字符，全大写或首字母大写）
        if 2 <= len(term) <= 4 and term.isupper():
            return TermType.SHORT_ACRONYM
        
        # 4. 检测驼峰/混合大小写
        if re.search(r'[a-z][A-Z]', term) or re.search(r'[A-Z][a-z][A-Z]', term):
            return TermType.MIXED_CASE
        
        # 5. 默认为普通词
        return TermType.COMMON_WORD
    
    @staticmethod
    def get_matching_strategy(term_type: TermType) -> dict:
        """获取匹配策略配置"""
        strategies = {
            TermType.SHORT_ACRONYM: {
                "case_sensitive": False,
                "word_boundary": True,
                "backtrack_validation": True,  # 需要回溯验证
                "min_context_chars": 1
            },
            TermType.MIXED_CASE: {
                "case_sensitive": False,
                "word_boundary": True,
                "backtrack_validation": False
            },
            TermType.COMMON_WORD: {
                "case_sensitive": False,
                "word_boundary": True,
                "backtrack_validation": False,
                "support_inflection": True  # 支持词形变化
            },
            TermType.SPECIAL_CHAR: {
                "case_sensitive": False,
                "word_boundary": False,  # 特殊字符本身就是边界
                "backtrack_validation": False
            },
            TermType.CHINESE: {
                "case_sensitive": True,
                "word_boundary": False,
                "backtrack_validation": False,
                "use_regex": False  # 中文不用正则
            }
        }
        return strategies[term_type]
```

**验收标准**：
- [ ] 正确分类所有测试用例（AI, CoWoS, memory, C++, 芯片）
- [ ] 边界情况处理（空字符串、纯数字、混合中英文）
- [ ] 单元测试覆盖率 > 95%

---

### Task 2.2: 实现模式编译器

**目标**：预编译正则表达式，提升匹配性能

**文件**：`src/services/term_matcher/pattern_compiler.py`

**核心功能**：

```python
import re
from functools import lru_cache

class PatternCompiler:
    """正则模式编译器"""
    
    def __init__(self):
        self._cache = {}
    
    @lru_cache(maxsize=1000)
    def compile_pattern(self, term: str, term_type: TermType, strategy: dict) -> re.Pattern:
        """编译术语匹配模式"""
        
        if term_type == TermType.CHINESE:
            # 中文不使用正则
            return None
        
        # 转义特殊字符
        escaped = re.escape(term)
        
        # 构建模式
        if term_type == TermType.SHORT_ACRONYM:
            # 短缩写：严格词边界
            pattern = rf'\b{escaped}\b'
        
        elif term_type == TermType.MIXED_CASE:
            # 驼峰词：词边界
            pattern = rf'\b{escaped}\b'
        
        elif term_type == TermType.COMMON_WORD:
            # 普通词：支持词形变化
            if strategy.get("support_inflection"):
                variants = self._generate_inflection_variants(term)
                pattern = rf'\b(?:{"|".join(re.escape(v) for v in variants)})\b'
            else:
                pattern = rf'\b{escaped}\b'
        
        elif term_type == TermType.SPECIAL_CHAR:
            # 特殊字符：不需要词边界
            pattern = escaped
        
        # 编译（大小写不敏感）
        flags = re.IGNORECASE if not strategy.get("case_sensitive") else 0
        return re.compile(pattern, flags)
    
    def _generate_inflection_variants(self, word: str) -> list[str]:
        """生成词形变体"""
        variants = [word]
        
        # 复数形式
        if word.endswith('y'):
            variants.append(word[:-1] + 'ies')  # memory → memories
        elif word.endswith(('s', 'x', 'z', 'ch', 'sh')):
            variants.append(word + 'es')
        else:
            variants.append(word + 's')
        
        # 过去式（简单规则）
        if word.endswith('e'):
            variants.append(word + 'd')
        else:
            variants.append(word + 'ed')
        
        # 进行时
        if word.endswith('e'):
            variants.append(word[:-1] + 'ing')
        else:
            variants.append(word + 'ing')
        
        return variants
```

**验收标准**：
- [ ] 正确编译所有术语类型的模式
- [ ] 词形变化生成准确（memory → memories, process → processed）
- [ ] 缓存机制有效（重复编译命中缓存）
- [ ] 单元测试覆盖率 > 90%

---

### Task 2.3: 实现匹配验证器

**目标**：回溯验证短缩写匹配，过滤误报

**文件**：`src/services/term_matcher/validator.py`

**核心逻辑**：

```python
class MatchValidator:
    """匹配验证器"""
    
    @staticmethod
    def validate_match(term: str, text: str, match: re.Match, term_type: TermType) -> bool:
        """验证匹配是否有效"""
        
        if term_type != TermType.SHORT_ACRONYM:
            return True  # 非短缩写直接通过
        
        # 短缩写需要回溯验证
        start, end = match.span()
        
        # 检查前后字符
        before = text[start-1] if start > 0 else ' '
        after = text[end] if end < len(text) else ' '
        
        # 规则：前后必须是非字母字符
        if before.isalpha() or after.isalpha():
            return False
        
        # 额外验证：避免 "AI" 匹配到 "DRAM" 中的 "AI"
        # 检查是否在一个更大的全大写单词中
        if start > 0 and end < len(text):
            # 向前扩展
            extended_start = start
            while extended_start > 0 and text[extended_start-1].isupper():
                extended_start -= 1
            
            # 向后扩展
            extended_end = end
            while extended_end < len(text) and text[extended_end].isupper():
                extended_end += 1
            
            # 如果扩展后的词比原术语长，说明是误报
            extended_word = text[extended_start:extended_end]
            if len(extended_word) > len(term) and extended_word != term.upper():
                return False
        
        return True
    
    @staticmethod
    def validate_context(term: str, text: str, match: re.Match, min_context_chars: int = 10) -> bool:
        """验证上下文（可选）"""
        start, end = match.span()
        
        # 提取上下文
        context_start = max(0, start - min_context_chars)
        context_end = min(len(text), end + min_context_chars)
        context = text[context_start:context_end]
        
        # 这里可以添加更复杂的上下文验证逻辑
        # 例如：检查是否在代码块、URL、邮箱中
        
        return True
```

**测试用例**：

```python
def test_short_acronym_validation():
    validator = MatchValidator()
    
    # 正例
    assert validator.validate_match("AI", "The AI system", match_at(4, 6), TermType.SHORT_ACRONYM) == True
    assert validator.validate_match("AI", "AI-powered", match_at(0, 2), TermType.SHORT_ACRONYM) == True
    
    # 反例
    assert validator.validate_match("AI", "DRAM", match_at(2, 4), TermType.SHORT_ACRONYM) == False
    assert validator.validate_match("AI", "SRAM", match_at(2, 4), TermType.SHORT_ACRONYM) == False
    assert validator.validate_match("HBM", "HBM3E", match_at(0, 3), TermType.SHORT_ACRONYM) == False  # HBM3E 是独立术语
```

**验收标准**：
- [ ] 正确过滤所有已知误报案例
- [ ] 不会过滤有效匹配
- [ ] 单元测试覆盖率 > 95%

---

### Task 2.4: 实现统一匹配接口

**目标**：提供简洁的匹配 API

**文件**：`src/services/term_matcher/matcher.py`

**核心接口**：

```python
from dataclasses import dataclass

@dataclass
class MatchResult:
    """匹配结果"""
    term: Term
    matched_text: str
    start: int
    end: int
    context: str  # 前后各 20 字符

class TermMatcher:
    """术语匹配器"""
    
    def __init__(self, terms: list[Term]):
        self.terms = terms
        self.classifier = TermClassifier()
        self.compiler = PatternCompiler()
        self.validator = MatchValidator()
        
        # 预编译所有术语
        self._compiled_terms = self._precompile_terms()
    
    def _precompile_terms(self) -> list[tuple[Term, TermType, re.Pattern, dict]]:
        """预编译所有术语"""
        compiled = []
        for term in self.terms:
            term_type = self.classifier.classify(term.original)
            strategy = self.classifier.get_matching_strategy(term_type)
            pattern = self.compiler.compile_pattern(term.original, term_type, strategy)
            compiled.append((term, term_type, pattern, strategy))
        return compiled
    
    def match_all(self, text: str) -> list[MatchResult]:
        """匹配文本中的所有术语"""
        results = []
        
        for term, term_type, pattern, strategy in self._compiled_terms:
            if term_type == TermType.CHINESE:
                # 中文直接子串匹配
                matches = self._match_chinese(term.original, text)
            else:
                # 使用正则匹配
                matches = pattern.finditer(text)
            
            for match in matches:
                # 验证匹配
                if self.validator.validate_match(term.original, text, match, term_type):
                    start, end = match.span()
                    context = self._extract_context(text, start, end)
                    results.append(MatchResult(
                        term=term,
                        matched_text=text[start:end],
                        start=start,
                        end=end,
                        context=context
                    ))
        
        # 按位置排序
        results.sort(key=lambda r: r.start)
        return results
    
    def match_term(self, term: Term, text: str) -> list[MatchResult]:
        """匹配单个术语"""
        # 类似 match_all，但只匹配一个术语
        pass
    
    def count_occurrences(self, term: Term, text: str) -> int:
        """统计术语出现次数"""
        return len(self.match_term(term, text))
    
    def _match_chinese(self, term: str, text: str) -> list:
        """中文子串匹配"""
        matches = []
        start = 0
        while True:
            pos = text.find(term, start)
            if pos == -1:
                break
            # 创建伪 Match 对象
            matches.append(type('Match', (), {'span': lambda: (pos, pos + len(term))})())
            start = pos + 1
        return matches
    
    def _extract_context(self, text: str, start: int, end: int, window: int = 20) -> str:
        """提取上下文"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
```

**验收标准**：
- [ ] match_all() 正确匹配所有术语
- [ ] 匹配结果按位置排序
- [ ] count_occurrences() 统计准确
- [ ] 性能：1000 个术语匹配 10KB 文本 < 100ms
- [ ] 单元测试覆盖率 > 90%

---

### Task 2.5: 编写综合测试

**目标**：验证匹配引擎的准确性和性能

**文件**：`tests/unit/services/test_term_matcher.py`

**测试用例集**：

```python
class TestTermMatcher:
    """术语匹配器综合测试"""
    
    def test_short_acronym_matching(self):
        """测试短缩写匹配"""
        terms = [
            Term(original="AI", translation="人工智能"),
            Term(original="HBM", translation="高带宽内存"),
        ]
        matcher = TermMatcher(terms)
        
        text = "AI chips use HBM memory. DRAM is different."
        results = matcher.match_all(text)
        
        assert len(results) == 2
        assert results[0].term.original == "AI"
        assert results[1].term.original == "HBM"
        
        # 验证不会误匹配 DRAM 中的 "AI"
        assert all(r.matched_text != "AI" or r.start != 35 for r in results)
    
    def test_mixed_case_matching(self):
        """测试驼峰词匹配"""
        terms = [Term(original="CoWoS", translation="CoWoS")]
        matcher = TermMatcher(terms)
        
        text = "CoWoS technology. cowos is the same. COWOS too."
        results = matcher.match_all(text)
        
        assert len(results) == 3  # 大小写不敏感
    
    def test_common_word_inflection(self):
        """测试普通词词形变化"""
        terms = [Term(original="memory", translation="内存")]
        matcher = TermMatcher(terms)
        
        text = "Memory chips. Multiple memories. Memorized data."
        results = matcher.match_all(text)
        
        assert len(results) == 2  # memory, memories
        assert results[0].matched_text.lower() == "memory"
        assert results[1].matched_text.lower() == "memories"
    
    def test_chinese_matching(self):
        """测试中文匹配"""
        terms = [Term(original="芯片", translation="chip")]
        matcher = TermMatcher(terms)
        
        text = "芯片设计和芯片制造是两个环节。"
        results = matcher.match_all(text)
        
        assert len(results) == 2
    
    def test_special_char_matching(self):
        """测试特殊字符术语"""
        terms = [Term(original="C++", translation="C++")]
        matcher = TermMatcher(terms)
        
        text = "C++ programming language"
        results = matcher.match_all(text)
        
        assert len(results) == 1
    
    def test_performance(self):
        """测试性能"""
        # 1000 个术语
        terms = [Term(original=f"term{i}", translation=f"术语{i}") for i in range(1000)]
        matcher = TermMatcher(terms)
        
        # 10KB 文本
        text = "term500 " * 1000
        
        import time
        start = time.time()
        results = matcher.match_all(text)
        elapsed = time.time() - start
        
        assert elapsed < 0.1  # < 100ms
        assert len(results) == 1000
```

**验收标准**：
- [ ] 所有测试通过
- [ ] 准确率 > 95%（手动标注 100 个样本验证）
- [ ] 性能达标
- [ ] 无已知误报案例

---

## 集成测试

**文件**：`tests/integration/test_term_matcher_integration.py`

**测试场景**：

1. **真实文档匹配**：
   - 使用 `projects/memory-mania/sections/00-intro/source.md`
   - 加载项目术语库
   - 验证匹配结果与人工标注一致

2. **跨语言匹配**：
   - 英文术语匹配英文文本
   - 中文术语匹配中文文本
   - 混合文本匹配

**验收标准**：
- [ ] 真实文档匹配准确率 > 95%
- [ ] 无性能问题

---

## 交付物

1. **代码**：
   - `src/services/term_matcher/classifier.py`
   - `src/services/term_matcher/pattern_compiler.py`
   - `src/services/term_matcher/validator.py`
   - `src/services/term_matcher/matcher.py`
   - `src/services/term_matcher/__init__.py`

2. **测试**：
   - `tests/unit/services/test_term_matcher.py`
   - `tests/integration/test_term_matcher_integration.py`

3. **文档**：
   - 更新 `docs/术语库系统手册.md` 的"术语匹配"章节
   - 添加匹配算法说明文档

---

## 验收标准

- [ ] 所有任务完成
- [ ] 单元测试覆盖率 > 90%
- [ ] 集成测试全部通过
- [ ] 匹配准确率 > 95%
- [ ] 性能达标（1000 术语 × 10KB 文本 < 100ms）
- [ ] 代码通过类型检查和格式检查

---

## 依赖和风险

**依赖**：
- Plan 1（Term 数据模型）

**风险**：
1. **词形变化规则不完整**
   - 缓解：使用 `inflect` 库或 `lemminflect` 库
   
2. **中文分词问题**
   - 缓解：当前使用简单子串匹配，未来可集成 jieba

3. **性能瓶颈**
   - 缓解：预编译正则、使用缓存、考虑使用 Aho-Corasick 算法

---

## 后续计划

完成 Plan 2 后，可以开始：
- **Plan 3**：术语确认流程（依赖 TermMatcher）
