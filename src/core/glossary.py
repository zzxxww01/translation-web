"""
Translation Agent - Glossary Manager

Manage global and project-specific glossaries.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict

from .models import Glossary, GlossaryTerm, TranslationStrategy


class GlossaryManager:
    """术语表管理器"""

    def __init__(self, global_path: str = "glossary", projects_path: str = "projects"):
        """
        初始化术语表管理器

        Args:
            global_path: 全局术语表目录
            projects_path: 项目目录
        """
        self.global_path = Path(global_path)
        self.projects_path = Path(projects_path)
        self.global_path.mkdir(parents=True, exist_ok=True)

    def load_global(self, domain: str = "semiconductor") -> Glossary:
        """
        加载全局术语表

        Args:
            domain: 领域名称（对应 glossary/{domain}.json）

        Returns:
            Glossary: 术语表
        """
        file_path = self.global_path / f"{domain}.json"
        if not file_path.exists():
            return Glossary()

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return Glossary(**data)

    def save_global(self, glossary: Glossary, domain: str = "semiconductor") -> None:
        """
        保存全局术语表

        Args:
            glossary: 术语表
            domain: 领域名称
        """
        glossary.version += 1
        file_path = self.global_path / f"{domain}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(glossary.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    def load_project(self, project_id: str) -> Glossary:
        """
        加载项目术语表

        Args:
            project_id: 项目 ID

        Returns:
            Glossary: 术语表
        """
        file_path = self.projects_path / project_id / "glossary.json"
        if not file_path.exists():
            return Glossary()

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return Glossary(**data)

    def save_project(self, project_id: str, glossary: Glossary) -> None:
        """
        保存项目术语表

        Args:
            project_id: 项目 ID
            glossary: 术语表
        """
        glossary.version += 1
        project_dir = self.projects_path / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        file_path = project_dir / "glossary.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(glossary.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    def merge(self, global_glossary: Glossary, project_glossary: Glossary) -> Glossary:
        """
        合并全局和项目术语表（项目优先）

        Args:
            global_glossary: 全局术语表
            project_glossary: 项目术语表

        Returns:
            Glossary: 合并后的术语表
        """
        merged = Glossary(version=max(global_glossary.version, project_glossary.version))

        # 先添加全局术语
        for term in global_glossary.terms:
            merged.add_term(term)

        # 再添加项目术语（会覆盖同名的全局术语）
        for term in project_glossary.terms:
            merged.add_term(term)

        return merged

    def load_merged(self, project_id: str, domain: str = "semiconductor") -> Glossary:
        """Load merged glossary with project terms overriding global terms."""
        return self.merge(
            self.load_global(domain),
            self.load_project(project_id),
        )

    def add_term(
        self,
        glossary: Glossary,
        original: str,
        translation: Optional[str],
        strategy: TranslationStrategy = TranslationStrategy.TRANSLATE,
        note: Optional[str] = None
    ) -> GlossaryTerm:
        """
        添加术语到术语表

        Args:
            glossary: 术语表
            original: 原文
            translation: 翻译
            strategy: 翻译策略
            note: 备注

        Returns:
            GlossaryTerm: 添加的术语
        """
        term = GlossaryTerm(
            original=original,
            translation=translation,
            strategy=strategy,
            note=note,
        )
        glossary.add_term(term)
        return term

    def get_term(self, glossary: Glossary, original: str) -> Optional[GlossaryTerm]:
        """
        查找术语

        Args:
            glossary: 术语表
            original: 原文

        Returns:
            Optional[GlossaryTerm]: 术语，如果不存在返回 None
        """
        return glossary.get_term(original)

    def apply_strategy(
        self,
        text: str,
        term: GlossaryTerm,
        is_first_occurrence: bool = False
    ) -> str:
        """
        应用术语翻译策略

        Args:
            text: 原文中的术语
            term: 术语定义
            is_first_occurrence: 是否是首次出现

        Returns:
            str: 翻译后的文本
        """
        if term.strategy == TranslationStrategy.PRESERVE:
            return text  # 保持原文

        if term.strategy == TranslationStrategy.FIRST_ANNOTATE:
            if is_first_occurrence and term.translation:
                return f"{term.translation}（{text}）"
            else:
                return term.translation or text

        # TRANSLATE 策略
        return term.translation or text

    def to_dict(self, glossary: Glossary) -> Dict[str, str]:
        """
        将术语表转换为简单字典（用于 prompt）

        Args:
            glossary: 术语表

        Returns:
            Dict[str, str]: {original: translation}
        """
        result = {}
        for term in glossary.terms:
            if getattr(term, "status", "active") != "active":
                continue
            if term.strategy == TranslationStrategy.PRESERVE:
                result[term.original] = f"[保持原文] {term.original}"
            elif term.strategy == TranslationStrategy.FIRST_ANNOTATE:
                result[term.original] = f"{term.translation}（首次标注原文）"
            else:
                result[term.original] = term.translation or term.original
        return result

    def to_list(self, glossary: Glossary) -> List[Dict]:
        """
        将术语表转换为列表格式（用于 prompt）

        Args:
            glossary: 术语表

        Returns:
            List[Dict]: 术语列表
        """
        return [
            term.model_dump(mode="json")
            for term in glossary.terms
            if getattr(term, "status", "active") == "active"
        ]

    def import_from_file(self, file_path: str) -> Glossary:
        """
        从文件导入术语表

        支持格式：
        - JSON: {"terms": [...]}
        - CSV: original,translation,strategy,note

        Args:
            file_path: 文件路径

        Returns:
            Glossary: 导入的术语表
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Glossary(**data)

        elif path.suffix == '.csv':
            import csv
            glossary = Glossary()
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    term = GlossaryTerm(
                        original=row.get('original', ''),
                        translation=row.get('translation'),
                        strategy=TranslationStrategy(row.get('strategy', 'translate')),
                        note=row.get('note')
                    )
                    glossary.add_term(term)
            return glossary

        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def export_to_file(self, glossary: Glossary, file_path: str) -> None:
        """
        导出术语表到文件

        Args:
            glossary: 术语表
            file_path: 文件路径
        """
        path = Path(file_path)

        if path.suffix == '.json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(glossary.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

        elif path.suffix == '.csv':
            import csv
            with open(path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['original', 'translation', 'strategy', 'note'])
                writer.writeheader()
                for term in glossary.terms:
                    writer.writerow({
                        'original': term.original,
                        'translation': term.translation or '',
                        'strategy': term.strategy.value,
                        'note': term.note or ''
                    })

        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")


def create_default_semiconductor_glossary() -> Glossary:
    """创建默认的半导体领域术语表"""
    glossary = Glossary(version=1)

    default_terms = [
        # ========== 公司与品牌 ==========
        ("TSMC", "台积电", TranslationStrategy.PRESERVE, "Taiwan Semiconductor Manufacturing Company"),
        ("Apple Silicon", None, TranslationStrategy.PRESERVE, "苹果自研芯片品牌"),
        ("NVIDIA", "英伟达", TranslationStrategy.PRESERVE, None),
        ("AMD", "AMD", TranslationStrategy.PRESERVE, "超微半导体"),
        ("Intel", "英特尔", TranslationStrategy.PRESERVE, None),
        ("Qualcomm", "高通", TranslationStrategy.PRESERVE, None),
        ("MediaTek", "联发科", TranslationStrategy.PRESERVE, None),
        ("Samsung", "三星", TranslationStrategy.PRESERVE, None),
        ("SK Hynix", "SK海力士", TranslationStrategy.PRESERVE, None),
        ("Micron", "美光", TranslationStrategy.PRESERVE, None),

        # ========== 芯片制造相关 ==========
        ("foundry", "晶圆代工厂", TranslationStrategy.FIRST_ANNOTATE, "后续可简称'代工厂'"),
        ("wafer", "晶圆", TranslationStrategy.TRANSLATE, None),
        ("fab", "晶圆厂", TranslationStrategy.FIRST_ANNOTATE, "fabrication facility"),
        ("node", "制程节点", TranslationStrategy.TRANSLATE, "如 7nm, 5nm, 3nm"),
        ("process", "工艺", TranslationStrategy.TRANSLATE, "指芯片制造工艺"),
        ("EUV", "EUV", TranslationStrategy.PRESERVE, "极紫外光刻 (Extreme Ultraviolet)"),
        ("EUV lithography", "EUV光刻", TranslationStrategy.FIRST_ANNOTATE, "极紫外光刻技术"),
        ("DUV", "DUV", TranslationStrategy.PRESERVE, "深紫外光刻 (Deep Ultraviolet)"),
        ("photolithography", "光刻", TranslationStrategy.TRANSLATE, None),
        ("etching", "蚀刻", TranslationStrategy.TRANSLATE, None),
        ("deposition", "沉积", TranslationStrategy.TRANSLATE, None),
        ("CMP", "化学机械抛光", TranslationStrategy.FIRST_ANNOTATE, "Chemical Mechanical Planarization"),

        # ========== 芯片类型与组件 ==========
        ("SoC", "SoC", TranslationStrategy.FIRST_ANNOTATE, "系统级芯片 (System on Chip)"),
        ("GPU", "GPU", TranslationStrategy.PRESERVE, "图形处理器"),
        ("CPU", "CPU", TranslationStrategy.PRESERVE, "中央处理器"),
        ("NPU", "NPU", TranslationStrategy.FIRST_ANNOTATE, "神经网络处理器"),
        ("TPU", "TPU", TranslationStrategy.FIRST_ANNOTATE, "张量处理器 (Tensor Processing Unit)"),
        ("chiplet", "芯粒", TranslationStrategy.FIRST_ANNOTATE, None),
        ("packaging", "封装", TranslationStrategy.TRANSLATE, None),
        ("CoWoS", "CoWoS", TranslationStrategy.PRESERVE, "Chip on Wafer on Substrate"),
        ("InFO", "InFO", TranslationStrategy.PRESERVE, "Integrated Fan-Out"),
        ("HBM", "HBM", TranslationStrategy.PRESERVE, "高带宽内存 (High Bandwidth Memory)"),
        ("SRAM", "SRAM", TranslationStrategy.PRESERVE, "静态随机存取存储器"),
        ("DRAM", "DRAM", TranslationStrategy.PRESERVE, "动态随机存取存储器"),
        ("NAND flash", "NAND闪存", TranslationStrategy.FIRST_ANNOTATE, None),
        ("logic chip", "逻辑芯片", TranslationStrategy.TRANSLATE, None),
        ("memory chip", "存储芯片", TranslationStrategy.TRANSLATE, None),
        ("analog chip", "模拟芯片", TranslationStrategy.TRANSLATE, None),
        ("RF chip", "射频芯片", TranslationStrategy.FIRST_ANNOTATE, "Radio Frequency"),

        # ========== AI/LLM 相关 ==========
        ("AI", "AI", TranslationStrategy.PRESERVE, "人工智能"),
        ("LLM", "LLM", TranslationStrategy.PRESERVE, "大语言模型 (Large Language Model)"),
        ("token", "token", TranslationStrategy.PRESERVE, "不翻译，保留原文"),
        ("context window", "上下文窗口", TranslationStrategy.TRANSLATE, None),
        ("inference", "推理", TranslationStrategy.TRANSLATE, None),
        ("training", "训练", TranslationStrategy.TRANSLATE, None),
        ("fine-tuning", "微调", TranslationStrategy.TRANSLATE, None),
        ("RLHF", "RLHF", TranslationStrategy.FIRST_ANNOTATE, "基于人类反馈的强化学习"),
        ("transformer", "Transformer", TranslationStrategy.PRESERVE, "一种深度学习模型架构"),
        ("attention", "注意力机制", TranslationStrategy.TRANSLATE, None),
        ("self-attention", "自注意力机制", TranslationStrategy.TRANSLATE, None),
        ("parameter", "参数", TranslationStrategy.TRANSLATE, None),
        ("weights", "权重", TranslationStrategy.TRANSLATE, None),
        ("model architecture", "模型架构", TranslationStrategy.TRANSLATE, None),
        ("neural network", "神经网络", TranslationStrategy.TRANSLATE, None),
        ("deep learning", "深度学习", TranslationStrategy.TRANSLATE, None),
        ("machine learning", "机器学习", TranslationStrategy.TRANSLATE, None),
        ("GPU cluster", "GPU集群", TranslationStrategy.FIRST_ANNOTATE, None),
        ("data center", "数据中心", TranslationStrategy.TRANSLATE, None),
        ("cloud computing", "云计算", TranslationStrategy.TRANSLATE, None),
        ("edge computing", "边缘计算", TranslationStrategy.TRANSLATE, None),

        # ========== 性能与指标 ==========
        ("throughput", "吞吐量", TranslationStrategy.TRANSLATE, None),
        ("latency", "延迟", TranslationStrategy.TRANSLATE, None),
        ("bandwidth", "带宽", TranslationStrategy.TRANSLATE, None),
        ("yield", "良率", TranslationStrategy.TRANSLATE, None),
        ("utilization rate", "利用率", TranslationStrategy.TRANSLATE, None),
        ("efficiency", "效率", TranslationStrategy.TRANSLATE, None),
        ("performance", "性能", TranslationStrategy.TRANSLATE, None),
        ("benchmark", "基准测试", TranslationStrategy.FIRST_ANNOTATE, None),
        ("FLOPS", "FLOPS", TranslationStrategy.PRESERVE, "每秒浮点运算次数"),
        ("TOPS", "TOPS", TranslationStrategy.PRESERVE, "每秒万亿次运算 (Trillions Operations Per Second)"),

        # ========== 商业与运营 ==========
        ("capex", "资本支出", TranslationStrategy.FIRST_ANNOTATE, "Capital Expenditure"),
        ("opex", "运营支出", TranslationStrategy.FIRST_ANNOTATE, "Operating Expense"),
        ("R&D", "研发", TranslationStrategy.TRANSLATE, "Research and Development"),
        ("IDM", "IDM", TranslationStrategy.FIRST_ANNOTATE, "垂直整合制造商 (Integrated Device Manufacturer)"),
        ("fabless", "无晶圆厂", TranslationStrategy.FIRST_ANNOTATE, "无晶圆厂设计公司"),
        ("anchor tenant", "锚定客户", TranslationStrategy.FIRST_ANNOTATE, "核心大客户"),
        ("gross margin", "毛利率", TranslationStrategy.TRANSLATE, None),
        ("revenue", "营收", TranslationStrategy.TRANSLATE, None),
        ("net income", "净收入", TranslationStrategy.TRANSLATE, None),
        ("market share", "市场份额", TranslationStrategy.TRANSLATE, None),
        ("supply chain", "供应链", TranslationStrategy.TRANSLATE, None),
        ("bottleneck", "瓶颈", TranslationStrategy.TRANSLATE, None),
        ("lead time", "交货周期", TranslationStrategy.FIRST_ANNOTATE, None),

        # ========== 其他技术术语 ==========
        ("HPC", "HPC", TranslationStrategy.PRESERVE, "高性能计算 (High Performance Computing)"),
        ("IoT", "IoT", TranslationStrategy.PRESERVE, "物联网 (Internet of Things)"),
        ("5G", "5G", TranslationStrategy.PRESERVE, "第五代移动通信技术"),
        ("semiconductor", "半导体", TranslationStrategy.TRANSLATE, None),
        ("integrated circuit", "集成电路", TranslationStrategy.FIRST_ANNOTATE, "IC"),
        ("transistor", "晶体管", TranslationStrategy.TRANSLATE, None),
        (" Moore's Law", "摩尔定律", TranslationStrategy.PRESERVE, None),
        ("virtualization", "虚拟化", TranslationStrategy.TRANSLATE, None),
        ("scalability", "可扩展性", TranslationStrategy.TRANSLATE, None),
    ]

    for original, translation, strategy, note in default_terms:
        glossary.add_term(GlossaryTerm(
            original=original,
            translation=translation,
            strategy=strategy,
            note=note
        ))

    return glossary
