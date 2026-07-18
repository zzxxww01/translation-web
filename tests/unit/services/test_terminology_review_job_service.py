import pytest

from src.services.terminology_review_job_service import (
    ActiveTerminologyReviewModelConflict,
    TerminologyReviewJobStore,
)


def test_term_review_job_store_reuses_active_job(tmp_path):
    store = TerminologyReviewJobStore(tmp_path)

    first, first_created = store.create_or_get_active("demo", "model-a")
    second, second_created = store.create_or_get_active("demo", "model-a")

    assert first_created is True
    assert second_created is False
    assert second["job_id"] == first["job_id"]
    assert second["status"] == "queued"


def test_term_review_job_store_rejects_active_job_from_another_model(tmp_path):
    store = TerminologyReviewJobStore(tmp_path)

    first, first_created = store.create_or_get_active("demo", "model-a")

    assert first_created is True
    with pytest.raises(ActiveTerminologyReviewModelConflict) as raised:
        store.create_or_get_active("demo", "model-b")

    assert raised.value.active_job["job_id"] == first["job_id"]
    assert raised.value.requested_model == "model-b"


def test_term_review_job_store_creates_new_job_after_completion(tmp_path):
    store = TerminologyReviewJobStore(tmp_path)

    first = store.create("demo")
    store.mark_succeeded("demo", first["job_id"], {"review_required": False})
    second = store.create("demo")

    assert second["job_id"] != first["job_id"]
    assert store.get("demo", first["job_id"])["result"] == {
        "review_required": False
    }


def test_term_review_job_store_replaces_orphan_after_worker_restart(tmp_path):
    first_store = TerminologyReviewJobStore(
        tmp_path,
        worker_epoch="worker-a",
    )
    orphaned, created = first_store.create_or_get_active("demo", "model-a")
    assert created is True
    first_store.mark_running("demo", orphaned["job_id"])

    restarted_store = TerminologyReviewJobStore(
        tmp_path,
        worker_epoch="worker-b",
    )
    replacement, replacement_created = restarted_store.create_or_get_active(
        "demo",
        "model-a",
    )

    assert replacement_created is True
    assert replacement["job_id"] != orphaned["job_id"]
    failed = restarted_store.get("demo", orphaned["job_id"])
    assert failed["status"] == "failed"
    assert "restarted" in failed["error"]
