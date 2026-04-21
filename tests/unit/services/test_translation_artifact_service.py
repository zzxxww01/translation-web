import json

from src.services.translation_artifact_service import TranslationArtifactService


def test_artifact_service_creates_run_dir(tmp_path):
    service = TranslationArtifactService(tmp_path)

    run_id, run_dir = service.create_run_artifact_dir("demo")

    assert run_id == run_dir.name
    assert run_dir.exists()
    assert run_dir.parent == tmp_path / "demo" / "artifacts" / "runs"


def test_artifact_service_infers_latest_run_state_from_summary(tmp_path):
    service = TranslationArtifactService(tmp_path)
    run_id, run_dir = service.create_run_artifact_dir("demo")
    summary = {
        "run_id": run_id,
        "status": "completed",
        "started_at": "2026-04-21T12:00:00",
        "finished_at": "2026-04-21T12:01:00",
        "error_count": 1,
    }
    (run_dir / "run-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False),
        encoding="utf-8",
    )

    inferred = service.infer_run_state("demo")

    assert inferred is not None
    assert inferred.run_id == run_id
    assert inferred.status == "completed"
    assert inferred.error_count == 1
