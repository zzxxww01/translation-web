"""
Translation Agent - CLI Commands

Command-line interface for the translation agent.
"""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.analysis import AnalysisAgent
from src.agents.consistency_reviewer import (
    ConsistencyReviewer,
    create_consistency_reviewer,
)
from src.agents.context_manager import LayeredContextManager, create_context_manager
from src.agents.deep_analyzer import DeepAnalyzer, create_deep_analyzer
from src.agents.four_step_translator import (
    FourStepTranslator,
    create_four_step_translator,
)
from src.agents.quality_gate import QualityGate, create_quality_gate
from src.agents.translation import TranslationAgent, TranslationContext
from src.core.glossary import GlossaryManager, create_default_semiconductor_glossary
from src.core.models import Glossary, GlossaryTerm, ParagraphStatus, TranslationStrategy
from src.core.project import ProjectManager
from src.llm.gemini import GeminiProvider

app = typer.Typer(help="Translation Agent CLI")
console = Console()

# 子命令组
glossary_app = typer.Typer(help="Glossary management")
app.add_typer(glossary_app, name="glossary")


def get_project_manager() -> ProjectManager:
    """获取项目管理器"""
    return ProjectManager(projects_path="projects")


def get_llm_provider() -> GeminiProvider:
    """获取 LLM Provider"""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_BACKUP_API_KEY")
    if not api_key:
        console.print("[red]错误: 请设置 GEMINI_API_KEY 环境变量[/red]")
        raise typer.Exit(1)
    return GeminiProvider(api_key=None, backup_api_key=api_key)


# ============ 项目管理命令 ============


@app.command()
def new(
    name: str = typer.Argument(..., help="项目名称"),
    html_file: str = typer.Argument(..., help="HTML 文件路径"),
):
    """创建新翻译项目"""
    pm = get_project_manager()

    with console.status(f"[bold green]正在创建项目 '{name}'..."):
        try:
            meta = pm.create(name, html_file)
            console.print("[green]项目创建成功![/green]")
            console.print(f"  ID: {meta.id}")
            console.print(f"  标题: {meta.title}")
            console.print(f"  章节数: {meta.progress.total_sections}")
            console.print(f"  段落数: {meta.progress.total_paragraphs}")
            console.print(f"\n项目目录: projects/{meta.id}/")
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")
            raise typer.Exit(1)


@app.command("list")
def list_projects():
    """列出所有项目"""
    pm = get_project_manager()
    projects = pm.list_all()

    if not projects:
        console.print("[yellow]暂无项目[/yellow]")
        return

    table = Table(title="翻译项目列表")
    table.add_column("ID", style="cyan")
    table.add_column("标题", style="white")
    table.add_column("状态", style="green")
    table.add_column("进度", style="yellow")
    table.add_column("创建时间", style="dim")

    for p in projects:
        progress = f"{p.progress.approved}/{p.progress.total_paragraphs}"
        percent = f"({p.progress.progress_percent:.1f}%)"
        table.add_row(
            p.id,
            p.title[:40] + "..." if len(p.title) > 40 else p.title,
            p.status.value,
            f"{progress} {percent}",
            p.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


@app.command()
def status(project: str = typer.Argument(..., help="项目 ID")):
    """查看项目状态"""
    pm = get_project_manager()

    try:
        meta = pm.get(project)
        sections = pm.get_sections(project)
    except FileNotFoundError:
        console.print(f"[red]项目不存在: {project}[/red]")
        raise typer.Exit(1)

    # 项目信息
    console.print(Panel(f"[bold]{meta.title}[/bold]", title="项目信息"))
    console.print(f"  ID: {meta.id}")
    console.print(f"  状态: {meta.status.value}")
    console.print(f"  创建时间: {meta.created_at}")
    console.print()

    # 进度
    progress = meta.progress
    console.print(
        f"[bold]进度:[/bold] {progress.approved}/{progress.total_paragraphs} ({progress.progress_percent:.1f}%)"
    )
    console.print()

    # 章节列表
    table = Table(title="章节列表")
    table.add_column("ID", style="cyan")
    table.add_column("标题", style="white")
    table.add_column("段落数", style="yellow")
    table.add_column("已完成", style="green")
    table.add_column("状态", style="dim")

    for s in sections:
        status_icon = (
            "[OK]" if s.is_complete else "[..]" if s.approved_count > 0 else "[  ]"
        )
        table.add_row(
            s.section_id,
            s.title[:30] + "..." if len(s.title) > 30 else s.title,
            str(s.total_paragraphs),
            str(s.approved_count),
            status_icon,
        )

    console.print(table)


@app.command()
def delete(
    project: str = typer.Argument(..., help="项目 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="强制删除，不确认"),
):
    """删除项目"""
    pm = get_project_manager()

    try:
        meta = pm.get(project)
    except FileNotFoundError:
        console.print(f"[red]项目不存在: {project}[/red]")
        raise typer.Exit(1)

    if not force:
        if not Confirm.ask(f"确定要删除项目 '{meta.title}'?"):
            console.print("已取消")
            return

    pm.delete(project)
    console.print(f"[green]项目已删除: {project}[/green]")


# ============ 翻译命令 ============


@app.command()
def analyze(
    project: str = typer.Argument(..., help="项目 ID"),
    deep: bool = typer.Option(False, "--deep", "-d", help="深度分析模式（四步法 Phase 0）"),
):
    """分析项目，提取术语和风格"""
    pm = get_project_manager()
    gm = GlossaryManager()

    try:
        meta = pm.get(project)
        sections = pm.get_sections(project)
    except FileNotFoundError:
        console.print(f"[red]项目不存在: {project}[/red]")
        raise typer.Exit(1)

    try:
        llm = get_llm_provider()
    except Exception as e:
        console.print(f"[red]初始化失败: {e}[/red]")
        raise typer.Exit(1)

    if deep:
        # 深度分析模式（四步法 Phase 0）
        with console.status("[bold green]正在进行深度分析..."):
            try:
                analyzer = create_deep_analyzer(llm)
                analysis = analyzer.analyze(sections)

                # 保存分析结果
                import json

                analysis_path = Path(f"projects/{project}/analysis.json")
                with open(analysis_path, "w", encoding="utf-8") as f:
                    json.dump(
                        analysis.model_dump(),
                        f,
                        ensure_ascii=False,
                        indent=2,
                        default=str,
                    )

                # 显示分析报告
                console.print("\n" + analyzer.get_analysis_summary(analysis))

                # 更新术语表
                existing = gm.load_project(project)
                for term in analysis.terminology:
                    new_term = GlossaryTerm(
                        original=term.term,
                        translation=term.translation,
                        strategy=term.strategy,
                        note=term.context_meaning,
                    )
                    existing.add_term(new_term)
                gm.save_project(project, existing)

                console.print(
                    f"\n[green]深度分析完成！结果已保存到 projects/{project}/analysis.json[/green]"
                )

            except Exception as e:
                console.print(f"[red]深度分析失败: {e}[/red]")
                import traceback

                traceback.print_exc()
                raise typer.Exit(1)
    else:
        # 原有简单分析模式
        with console.status("[bold green]正在分析文章..."):
            try:
                agent = AnalysisAgent(llm)
                result = agent.analyze(sections)

                # 合并术语表
                existing = gm.load_project(project)
                merged = agent.merge_glossary(existing, result.detected_terms)
                gm.save_project(project, merged)

                console.print("[green]分析完成![/green]")
                console.print(f"  检测到 {len(result.detected_terms)} 个术语")
                console.print(
                    f"  风格: {result.style_guide.tone}, {result.style_guide.formality}"
                )

                if result.summary:
                    console.print(f"\n[bold]摘要:[/bold] {result.summary}")

            except Exception as e:
                console.print(f"[red]分析失败: {e}[/red]")
                raise typer.Exit(1)


@app.command()
def translate(
    project: str = typer.Argument(..., help="项目 ID"),
    section: Optional[str] = typer.Option(None, "--section", "-s", help="指定章节 ID"),
    auto: bool = typer.Option(False, "--auto", "-a", help="自动模式，不逐段确认"),
    mode: str = typer.Option(
        "simple", "--mode", "-m", help="翻译模式: simple(简单) / four-step(四步)"
    ),
    quality: str = typer.Option(
        "strict", "--quality", "-q", help="质量门禁: strict/standard/relaxed"
    ),
):
    """翻译项目"""
    pm = get_project_manager()
    gm = GlossaryManager()

    try:
        meta = pm.get(project)
        sections = pm.get_sections(project)
        glossary = gm.load_project(project)
    except FileNotFoundError:
        console.print(f"[red]项目不存在: {project}[/red]")
        raise typer.Exit(1)

    # 筛选章节
    if section:
        sections = [s for s in sections if s.section_id == section]
        if not sections:
            console.print(f"[red]章节不存在: {section}[/red]")
            raise typer.Exit(1)

    try:
        llm = get_llm_provider()
    except Exception as e:
        console.print(f"[red]初始化失败: {e}[/red]")
        raise typer.Exit(1)

    if mode == "four-step":
        # 四步法翻译模式
        _translate_four_step(pm, gm, llm, project, sections, quality)
    else:
        # 原有简单翻译模式
        _translate_simple(pm, llm, project, sections, glossary, auto)


def _translate_four_step(pm, gm, llm, project: str, sections, quality: str):
    """四步法翻译"""
    import json

    # 加载或创建深度分析结果
    analysis_path = Path(f"projects/{project}/analysis.json")
    if analysis_path.exists():
        with open(analysis_path, "r", encoding="utf-8") as f:
            from src.core.models import ArticleAnalysis

            analysis_data = json.load(f)
            analysis = ArticleAnalysis(**analysis_data)
        console.print("[dim]已加载深度分析结果[/dim]")
    else:
        console.print("[yellow]未找到深度分析结果，正在进行深度分析...[/yellow]")
        analyzer = create_deep_analyzer(llm)
        analysis = analyzer.analyze(sections)
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(
                analysis.model_dump(), f, ensure_ascii=False, indent=2, default=str
            )
        console.print("[green]深度分析完成[/green]")

    # 创建四步法组件
    context_manager = create_context_manager(analysis)
    quality_gate = create_quality_gate(mode=quality)
    translator = create_four_step_translator(
        llm_provider=llm,
        context_manager=context_manager,
        quality_gate=quality_gate,
        paragraph_threshold=8,
    )

    console.print(f"\n[bold cyan]开始四步法翻译 (质量门禁: {quality})[/bold cyan]")
    console.print(f"主题: {analysis.theme}")
    console.print(f"章节数: {len(sections)}")
    console.print()

    all_translations = {}
    all_sections_list = pm.get_sections(project)  # 获取完整章节列表用于上下文
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        main_task = progress.add_task("[cyan]翻译进度", total=len(sections))

        for sec in sections:
            progress.update(main_task, description=f"[cyan]章节: {sec.title[:30]}...")

            # 定义进度回调
            def on_progress(step_name: str, current: int, total: int):
                progress.update(
                    main_task, description=f"[cyan]{sec.section_id}: {step_name}"
                )

            try:
                result = translator.translate_section(
                    section=sec, all_sections=all_sections_list, on_progress=on_progress
                )

                all_translations[sec.section_id] = result.translations

                # 显示结果
                status_icon = "[OK]" if result.assessment.passed else "[WARN]"
                console.print(f"\n{status_icon} [bold]{sec.title}[/bold]")
                console.print(f"   评分: {result.assessment.overall_score:.1f}/10")
                console.print(
                    f"   可读性: {result.reflection.readability_score:.1f} | 准确性: {result.reflection.accuracy_score:.1f}"
                )

                if not result.assessment.passed:
                    console.print(
                        f"   [yellow]未通过原因: {', '.join(result.assessment.failed_criteria)}[/yellow]"
                    )

                # 保存翻译结果到段落
                for i, (para, trans) in enumerate(
                    zip(sec.paragraphs, result.translations)
                ):
                    para.add_translation(trans, "gemini-four-step")
                    para.confirm(trans, "gemini-four-step")

                pm.save_section(project, sec)

            except Exception as e:
                console.print(f"\n[red]章节 {sec.section_id} 翻译失败: {e}[/red]")
                import traceback

                traceback.print_exc()

            progress.advance(main_task)

    # Phase 2: 一致性审查
    console.print("\n[bold cyan]Phase 2: 全文一致性审查[/bold cyan]")

    with console.status("[bold green]审查..."):
        reviewer = create_consistency_reviewer(llm)
        report = reviewer.review(
            sections=sections,
            translations=all_translations,
            article_analysis=analysis,
            term_tracker=context_manager.term_tracker,
        )

    console.print(reviewer.get_review_report(report))

    # 保存审查报告
    report_path = Path(f"projects/{project}/consistency_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, ensure_ascii=False, indent=2, default=str)

    console.print("\n[green]四步法翻译完成！[/green]")
    console.print(f"  审查报告: projects/{project}/consistency_report.json")


def _translate_simple(pm, llm, project: str, sections, glossary, auto: bool):
    """简单翻译模式（原有逻辑）"""
    agent = TranslationAgent(llm)
    context = TranslationContext(glossary=glossary)

    for sec in sections:
        console.print(f"\n[bold cyan]章节: {sec.title}[/bold cyan]")

        for i, para in enumerate(sec.paragraphs):
            # 跳过已确认的
            if para.status == ParagraphStatus.APPROVED:
                console.print(f"  [dim]段落 {para.id}: 已确认，跳过[/dim]")
                agent.context_window.add_confirmed(para.source, para.confirmed)
                continue

            # 显示原文
            console.print(f"\n[yellow]段落 {para.id}[/yellow]")
            console.print(
                Panel(
                    (
                        para.source[:500] + "..."
                        if len(para.source) > 500
                        else para.source
                    ),
                    title="原文",
                )
            )

            # 翻译
            with console.status("[bold green]翻译中..."):
                context.previous_paragraphs = agent.context_window.get_context()
                context.next_preview = [p.source for p in sec.paragraphs[i + 1 : i + 3]]
                translation = agent.translate_paragraph(para, context, "gemini")

            # 显示译文
            console.print(Panel(translation, title="译文"))

            if auto:
                # 自动模式：直接确认
                para.confirm(translation, "gemini")
                agent.context_window.add_confirmed(para.source, translation)
                console.print("[green]已自动确认[/green]")
            else:
                # 交互模式
                action = Prompt.ask(
                    "操作 [y=确认/n=跳过/e=编辑/s=跳过/q=退出]",
                    choices=["y", "n", "e", "s", "q"],
                    default="y",
                )

                if action == "y":
                    para.confirm(translation, "gemini")
                    agent.context_window.add_confirmed(para.source, translation)
                    console.print("[green]已确认[/green]")
                elif action == "e":
                    edited = Prompt.ask("输入修改后的译文")
                    para.confirm(edited, "manual")
                    agent.context_window.add_confirmed(para.source, edited)
                    console.print("[green]已保存修改[/green]")
                elif action == "s":
                    console.print("[yellow]已跳过[/yellow]")
                elif action == "q":
                    console.print("[yellow]退出翻译[/yellow]")
                    pm.save_section(project, sec)
                    return
                else:
                    console.print("[yellow]已跳过[/yellow]")

        # 保存章节
        pm.save_section(project, sec)
        console.print(f"[green]章节 {sec.section_id} 已保存[/green]")

    console.print("\n[green]翻译完成![/green]")


@app.command()
def export(
    project: str = typer.Argument(..., help="项目 ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径"),
    include_source: bool = typer.Option(False, "--source", help="包含原文注释"),
):
    """导出翻译结果"""
    pm = get_project_manager()

    try:
        content = pm.export(project, include_source=include_source)
        output_path = output or f"projects/{project}/output.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[green]已导出到: {output_path}[/green]")
    except FileNotFoundError:
        console.print(f"[red]项目不存在: {project}[/red]")
        raise typer.Exit(1)


# ============ 术语表命令 ============


@glossary_app.command("list")
def glossary_list(
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="项目 ID（不指定则显示全局）"
    )
):
    """查看术语表"""
    gm = GlossaryManager()

    if project:
        glossary = gm.load_project(project)
        title = f"项目术语表: {project}"
    else:
        glossary = create_default_semiconductor_glossary()
        title = "全局术语表（半导体）"

    if not glossary.terms:
        console.print("[yellow]术语表为空[/yellow]")
        return

    table = Table(title=title)
    table.add_column("原文", style="cyan")
    table.add_column("翻译", style="white")
    table.add_column("策略", style="green")
    table.add_column("备注", style="dim")

    strategy_map = {
        "preserve": "保持原文",
        "first_annotate": "首次标注",
        "translate": "翻译",
    }

    for term in glossary.terms:
        table.add_row(
            term.original,
            term.translation or "-",
            strategy_map.get(term.strategy.value, term.strategy.value),
            term.note or "-",
        )

    console.print(table)


@glossary_app.command("add")
def glossary_add(
    term: str = typer.Argument(..., help="英文术语"),
    translation: str = typer.Argument(..., help="中文翻译"),
    strategy: str = typer.Option(
        "translate", "--strategy", "-s", help="策略: preserve/first_annotate/translate"
    ),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="备注"),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="项目 ID（不指定则添加到全局）"
    ),
):
    """添加术语"""
    gm = GlossaryManager()

    try:
        strat = TranslationStrategy(strategy)
    except ValueError:
        console.print(f"[red]无效的策略: {strategy}[/red]")
        raise typer.Exit(1)

    if project:
        glossary = gm.load_project(project)
    else:
        glossary = gm.load_global("semiconductor")

    new_term = GlossaryTerm(
        original=term,
        translation=translation if strat != TranslationStrategy.PRESERVE else None,
        strategy=strat,
        note=note,
    )
    glossary.add_term(new_term)

    if project:
        gm.save_project(project, glossary)
    else:
        gm.save_global(glossary, "semiconductor")

    console.print(f"[green]已添加术语: {term} → {translation}[/green]")


@glossary_app.command("init")
def glossary_init():
    """初始化全局术语表（半导体领域）"""
    gm = GlossaryManager()
    glossary = create_default_semiconductor_glossary()
    gm.save_global(glossary, "semiconductor")
    console.print(
        f"[green]已初始化全局术语表，包含 {len(glossary.terms)} 个术语[/green]"
    )


# ============ 服务命令 ============


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="主机地址"),
    port: int = typer.Option(54321, "--port", "-p", help="端口"),
):
    """启动 Web 服务"""
    try:
        import uvicorn

        console.print(f"[green]启动 Web 服务: http://{host}:{port}[/green]")
        uvicorn.run("src.api.app:app", host=host, port=port, reload=True)
    except ImportError:
        console.print("[red]请安装 uvicorn: pip install uvicorn[/red]")
        raise typer.Exit(1)


# ============ 入口 ============


def main():
    """CLI 入口"""
    app()


if __name__ == "__main__":
    main()
