"""

Term Matcher - 术语匹配器



智能匹配段落中的相关术语，避免注入无关术语导致 token 浪费。

"""



from dataclasses import dataclass

from typing import List, Dict, Optional, Set

import re

from src.core.models import Glossary, GlossaryTerm, TranslationStrategy





@dataclass

class MatchResult:

    """术语匹配结果"""

    term: GlossaryTerm

    score: float

    match_type: str  # exact, partial





class TermMatcher:

    """术语匹配器"""



    def __init__(self, glossary: Glossary):

        """

        初始化术语匹配器



        Args:

            glossary: 术语表

        """

        self.glossary = glossary

        # 构建术语索引

        self._build_index()



    def _build_index(self) -> None:

        """构建术语索引，加速匹配"""

        self.exact_matches: Dict[str, GlossaryTerm] = {}

        self.partial_matches: Dict[str, GlossaryTerm] = {}



        for term in self.glossary.terms:

            original_lower = term.original.lower()

            # 精确匹配索引

            self.exact_matches[original_lower] = term



            # 对于多词术语，添加部分匹配索引

            words = original_lower.split()

            if len(words) > 1:

                for word in words:

                    if len(word) > 3:  # 只索引长度大于3的单词

                        if word not in self.partial_matches:

                            self.partial_matches[word] = term



    def _tokenize(self, text: str) -> Set[str]:

        """

        分词



        Args:

            text: 输入文本



        Returns:

            Set[str]: 词集合

        """

        # 转换为小写

        text = text.lower()

        # 移除标点符号

        text = re.sub(r'[^\w\s]', ' ', text)

        # 分词

        words = set(text.split())

        return words



    def _calculate_exact_score(self, paragraph: str, term: GlossaryTerm) -> float:

        """

        计算精确匹配分数



        Args:

            paragraph: 段落文本

            term: 术语



        Returns:

            float: 匹配分数

        """

        original_lower = term.original.lower()

        paragraph_lower = paragraph.lower()



        # 完整出现

        if original_lower in paragraph_lower:

            # 计算出现次数

            count = paragraph_lower.count(original_lower)

            # 基础分数 + 出现次数加成

            score = 1.0 + min(count * 0.1, 0.5)



            # 如果是较短的术语（可能不够独特），降低分数

            if len(term.original.split()) == 1 and len(term.original) < 5:

                score *= 0.7



            return score



        return 0.0



    def _calculate_partial_score(self, paragraph: str, term: GlossaryTerm) -> float:

        """

        计算部分匹配分数（基于词根）



        Args:

            paragraph: 段落文本

            term: 术语



        Returns:

            float: 匹配分数

        """

        paragraph_words = self._tokenize(paragraph)

        term_words = self._tokenize(term.original)



        if not term_words:

            return 0.0



        # 计算重叠比例

        overlap = paragraph_words & term_words

        if not overlap:

            return 0.0



        # 重叠比例 = 重叠词数 / 术语词数

        overlap_ratio = len(overlap) / len(term_words)



        # 部分匹配的分数最高为 0.7（低于精确匹配）

        score = overlap_ratio * 0.7



        # 如果术语是单个词，需要完整匹配才算

        if len(term_words) == 1:

            return 0.0



        return score



    def match_paragraph(

        self,

        paragraph: str,

        max_terms: int = 20,

        min_score: float = 0.3

    ) -> List[MatchResult]:

        """

        匹配段落中的相关术语



        Args:

            paragraph: 段落文本

            max_terms: 最大返回术语数量

            min_score: 最低匹配分数阈值



        Returns:

            List[MatchResult]: 匹配结果列表，按分数降序排列

        """

        results: List[MatchResult] = []



        for term in self.glossary.terms:

            # 先尝试精确匹配

            exact_score = self._calculate_exact_score(paragraph, term)



            if exact_score > 0:

                results.append(MatchResult(

                    term=term,

                    score=exact_score,

                    match_type="exact"

                ))

                continue



            # 再尝试部分匹配

            partial_score = self._calculate_partial_score(paragraph, term)

            if partial_score >= min_score:

                results.append(MatchResult(

                    term=term,

                    score=partial_score,

                    match_type="partial"

                ))



        # 按分数降序排序

        results.sort(key=lambda x: x.score, reverse=True)



        # 限制返回数量

        return results[:max_terms]



    def detect_terms_in_translation(

        self,

        source: str,

        translation: str

    ) -> Dict[str, bool]:

        """

        检测译文是否使用了术语



        Args:

            source: 原文

            translation: 译文



        Returns:

            Dict[str, bool]: 术语原文 -> 是否正确使用

        """

        results: Dict[str, bool] = {}



        for term in self.glossary.terms:

            original_lower = term.original.lower()



            # 检查原文是否包含术语

            if original_lower not in source.lower():

                continue



            # 根据策略检查译文

            if term.strategy == TranslationStrategy.PRESERVE:

                # 应该保留英文

                results[term.original] = term.original.lower() in translation.lower()

            elif term.strategy == TranslationStrategy.TRANSLATE:

                # 应该翻译成中文

                if term.translation:

                    results[term.original] = term.translation in translation

                else:

                    # 没有指定翻译，无法判断

                    results[term.original] = True

            elif term.strategy == TranslationStrategy.FIRST_ANNOTATE:

                # 首次出现需要注释

                results[term.original] = (

                    term.translation in translation if term.translation else True

                )



        return results



    def get_term_context(

        self,

        paragraph: str,

        max_terms: int = 20

    ) -> List[Dict]:

        """

        获取用于 LLM 上下文的术语列表



        Args:

            paragraph: 段落文本

            max_terms: 最大术语数量



        Returns:

            List[Dict]: 术语上下文列表

        """

        matches = self.match_paragraph(paragraph, max_terms)



        return [

            {

                "original": m.term.original,

                "translation": m.term.translation,

                "strategy": m.term.strategy.value,

                "note": m.term.note,

                "match_score": m.score,

                "match_type": m.match_type

            }

            for m in matches

        ]





def filter_relevant_terms(

    glossary: Glossary,

    paragraph: str,

    max_terms: int = 20

) -> List[GlossaryTerm]:

    """

    筛选段落相关的术语



    Args:

        glossary: 术语表

        paragraph: 段落文本

        max_terms: 最大返回术语数量



    Returns:

        List[GlossaryTerm]: 相关术语列表

    """

    matcher = TermMatcher(glossary)

    matches = matcher.match_paragraph(paragraph, max_terms)

    return [m.term for m in matches]
