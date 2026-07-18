import json

from src.services.quality_report_service import QualityReportService


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _build_run(tmp_path):
    run_dir = (
        tmp_path
        / "projects"
        / "demo"
        / "artifacts"
        / "runs"
        / "20260719-120000-test"
    )
    _write_json(
        run_dir / "run-summary.json",
        {
            "project_id": "demo",
            "started_at": "2026-07-19T12:00:00",
            "status": "completed",
        },
    )
    _write_json(
        run_dir / "section-critique" / "s1.json",
        {
            "section_id": "s1",
            "reflection": {
                "overall_score": 82,
                "readability_score": 80,
                "accuracy_score": 84,
                "conciseness_score": 81,
                "is_excellent": False,
                "issues": [
                    {
                        "paragraph_index": 0,
                        "issue_type": "accuracy",
                        "description": "Meaning needs refinement",
                    }
                ],
            },
        },
    )
    _write_json(
        run_dir / "section-revision" / "s1.json",
        {
            "section_id": "s1",
            "translations": ["修订后的译文"],
            "revision_attempted": True,
        },
    )
    _write_json(
        run_dir / "consistency.json",
        {
            "report": {
                "auto_fixable": [
                    {
                        "section_id": "s1",
                        "paragraph_index": 0,
                        "issue_type": "terminology",
                        "description": "Can be fixed automatically",
                    }
                ]
            }
        },
    )
    return run_dir


def test_revision_is_attempted_but_not_reported_as_verified_fix(tmp_path):
    run_dir = _build_run(tmp_path)
    service = QualityReportService(tmp_path)

    report = service.get_report_by_run_id(
        run_id=run_dir.name,
        project_id="demo",
    )

    assert report is not None
    assert report.total_issues == 2
    assert report.auto_fixed_issues == 0
    assert report.revision_attempted_issues == 1
    assert report.manual_review_issues == 2

    critique_issue = next(
        issue for issue in report.issues if issue.issue_type == "accuracy"
    )
    assert critique_issue.auto_fixed is False
    assert critique_issue.revision_attempted is True
    assert critique_issue.revised_text == "修订后的译文"

    consistency_issue = next(
        issue for issue in report.issues if issue.issue_type == "terminology"
    )
    assert consistency_issue.auto_fixed is False
    assert consistency_issue.auto_fixable is True

    section = report.sections[0]
    assert section.auto_fixed_count == 0
    assert section.revision_attempted_count == 1
    assert section.manual_review_count == 1


def test_section_issues_expose_revision_attempt_without_auto_fix(tmp_path):
    run_dir = _build_run(tmp_path)
    service = QualityReportService(tmp_path)

    issues = service.get_section_issues(
        run_id=run_dir.name,
        section_id="s1",
        project_id="demo",
    )

    assert len(issues) == 1
    assert issues[0].auto_fixed is False
    assert issues[0].revision_attempted is True
    assert issues[0].revised_text == "修订后的译文"


def test_revision_artifact_without_attempt_flag_is_not_reported_as_attempted(
    tmp_path,
):
    run_dir = _build_run(tmp_path)
    revision_file = run_dir / "section-revision" / "s1.json"
    payload = json.loads(revision_file.read_text(encoding="utf-8"))
    payload.pop("revision_attempted")
    _write_json(revision_file, payload)

    report = QualityReportService(tmp_path).get_report_by_run_id(
        run_id=run_dir.name,
        project_id="demo",
    )

    assert report is not None
    issue = next(item for item in report.issues if item.issue_type == "accuracy")
    assert issue.revision_attempted is False
    assert issue.revised_text is None
