#!/usr/bin/env python3
"""Tests for background pipeline jobs (web/jobs.py) and the /api/jobs endpoints.

Most tests run tiny `python -c` scripts as job steps, so they exercise real
subprocesses, streaming, progress parsing and cancellation without touching
the pipeline. One test runs the real filter -> summarize dry run end to end in
a throwaway project home.
"""

import os
import shutil
import sys
import textwrap
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from firm_analyzer.web import app as web  # noqa: E402
from firm_analyzer.web import jobs as jobs_module  # noqa: E402
from firm_analyzer.web.jobs import (  # noqa: E402
    Job,
    JobConflict,
    JobError,
    JobManager,
    Step,
    build_steps,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = {"categories": [{"id": "ai_ml"}, {"id": "general"}]}
WAIT = 30


def script(code: str) -> Step:
    return Step("fake", [sys.executable, "-u", "-c", textwrap.dedent(code)])


PROGRESS_SCRIPT = script(
    """
    import sys
    print("Loaded 3 firms to process.")
    for i in range(1, 4):
        print(f"Processing [{i}/3] firm{i}...")
    print("traceback-ish secret /home/me/.env", file=sys.stderr)
    print("Summary: 3 processed, 0 already done, 0 failed.")
    """
)
SLEEP_SCRIPT = script(
    """
    import time
    print("Processing [1/100] slow...")
    time.sleep(60)
    """
)
FAIL_SCRIPT = script(
    """
    import sys
    print("Error: input not found.")
    print("Traceback: secret detail", file=sys.stderr)
    sys.exit(2)
    """
)


@pytest.fixture
def manager(tmp_path):
    m = JobManager(cwd=tmp_path)
    yield m
    m.shutdown()


def run_to_end(manager, steps, kind="summarize"):
    job = manager.start(kind, {}, steps)
    assert job.done.wait(WAIT), "job did not finish"
    return job


# --- build_steps -------------------------------------------------------------

def test_summarize_options_map_onto_fixed_flags():
    (step,) = build_steps(
        "summarize",
        {"dry_run": True, "limit": "5", "provider": "gemini", "no_segmentation": True},
        CONFIG,
    )
    assert step.argv[:4] == [sys.executable, "-u", "-m", "firm_analyzer.core.summarize"]
    assert step.argv[4:] == ["--dry-run", "--limit", "5", "--provider", "gemini", "--no-segmentation"]


def test_defaults_add_no_flags():
    (step,) = build_steps("summarize", {}, CONFIG)
    assert step.argv[4:] == []


def test_pipeline_is_filter_then_summarize():
    steps = build_steps("pipeline", {"limit": 3}, CONFIG)
    assert [s.name for s in steps] == ["filter", "summarize"]
    assert steps[0].argv[4:] == []
    assert steps[1].argv[4:] == ["--limit", "3"]


def test_segment_options():
    (step,) = build_steps(
        "segment",
        {"relocate": True, "force": True, "categories": ["general", "ai_ml"], "limit": 10},
        CONFIG,
    )
    assert step.argv[3] == "firm_analyzer.core.resegment"
    assert step.argv[4:] == [
        "--limit", "10", "--relocate", "--force", "--category", "general", "--category", "ai_ml",
    ]


@pytest.mark.parametrize(
    "kind, options",
    [
        ("rm", {}),
        (None, {}),
        ("filter", {"limit": 3}),                 # filter takes no options
        ("summarize", {"limit": "abc"}),
        ("summarize", {"limit": 0}),
        ("summarize", {"limit": True}),
        ("summarize", {"limit": 10**9}),
        ("summarize", {"dry_run": "yes"}),
        ("summarize", {"provider": "evil; rm -rf /"}),
        ("summarize", {"extra": "--output-dir=/"}),
        ("summarize", ["not", "an", "object"]),
        ("segment", {"categories": ["../etc"]}),
        ("segment", {"categories": "general"}),
    ],
)
def test_invalid_requests_are_rejected(kind, options):
    with pytest.raises(JobError):
        build_steps(kind, options, CONFIG)


# --- Job log and progress ------------------------------------------------------

def test_progress_and_summary_are_parsed_from_output():
    job = Job(kind="summarize", options={}, steps=[])
    job.append("Loaded 10 firms to process.")
    job.append("Skipping [4/10] 알파 (already processed).")
    assert job.progress == {"current": 4, "total": 10}
    job.append("[7/10] general/베타")  # segment's format
    assert job.progress == {"current": 7, "total": 10}
    job.append("  -> Would search: [1/2] is not a progress line")
    assert job.progress == {"current": 7, "total": 10}
    job.append("Summary: 6 processed, 3 already done, 1 failed.")
    assert job.summary == "Summary: 6 processed, 3 already done, 1 failed."


def test_log_is_windowed_by_since(monkeypatch):
    monkeypatch.setattr(jobs_module, "MAX_LOG_LINES", 5)
    job = Job(kind="filter", options={}, steps=[])
    for i in range(8):
        job.append(f"line {i}")

    full = job.to_dict(since=0)
    assert full["log"] == [f"line {i}" for i in range(3, 8)]
    assert (full["log_start"], full["log_next"], full["log_truncated"]) == (3, 8, True)

    tail = job.to_dict(since=6)
    assert tail["log"] == ["line 6", "line 7"]
    assert tail["log_truncated"] is False
    assert job.to_dict(since=8)["log"] == []
    assert "log" not in job.to_dict()


# --- JobManager ----------------------------------------------------------------

def test_successful_job_streams_stdout_but_not_stderr(manager):
    job = run_to_end(manager, [PROGRESS_SCRIPT])
    data = job.to_dict(since=0)
    assert data["status"] == "succeeded"
    assert data["progress"] == {"current": 3, "total": 3}
    assert data["summary"].startswith("Summary: 3 processed")
    assert data["log"][0] == "▶ fake"
    assert "Processing [2/3] firm2..." in data["log"]
    assert not any("secret" in line for line in data["log"])
    assert data["elapsed"] is not None and data["finished_at"] >= data["started_at"]


def test_failed_step_stops_the_job_and_hides_stderr(manager):
    job = run_to_end(manager, [FAIL_SCRIPT, PROGRESS_SCRIPT], kind="pipeline")
    data = job.to_dict(since=0)
    assert data["status"] == "failed"
    assert data["returncode"] == 2
    assert "exit 2" in data["error"]
    assert "Error: input not found." in data["log"]
    assert data["log"].count("▶ fake") == 1  # the second step never ran
    assert "secret" not in str(data)


def test_only_one_job_runs_at_a_time(manager):
    first = manager.start("summarize", {}, [SLEEP_SCRIPT])
    with pytest.raises(JobConflict) as conflict:
        manager.start("filter", {}, [PROGRESS_SCRIPT])
    assert conflict.value.active is first
    manager.cancel(first.id)
    assert first.done.wait(WAIT)
    # Free again once the first one is over.
    assert run_to_end(manager, [PROGRESS_SCRIPT]).status == "succeeded"


def test_cancel_terminates_the_subprocess(manager):
    job = manager.start("summarize", {}, [SLEEP_SCRIPT, PROGRESS_SCRIPT])
    # Wait until the first step is actually running.
    for _ in range(200):
        if job.progress:
            break
        job.done.wait(0.05)
    manager.cancel(job.id)
    assert job.done.wait(WAIT)
    assert job.status == "cancelled"
    assert job.error == "Cancelled."
    assert job.to_dict(since=0)["log"].count("▶ fake") == 1


def test_timeout_cancels_a_long_job(tmp_path):
    manager = JobManager(cwd=tmp_path, timeout=0.5)
    job = manager.start("summarize", {}, [SLEEP_SCRIPT])
    assert job.done.wait(WAIT)
    assert job.status == "cancelled"
    assert "Timed out" in job.error


def test_old_finished_jobs_are_trimmed(tmp_path):
    manager = JobManager(cwd=tmp_path, max_jobs=2)
    ids = [run_to_end(manager, [PROGRESS_SCRIPT]).id for _ in range(3)]
    # Newest first; the oldest finished job was dropped.
    assert [job.id for job in manager.list()] == [ids[2], ids[1]]


# --- HTTP API ------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch, tmp_path):
    manager = JobManager(cwd=tmp_path)
    monkeypatch.setattr(web, "jobs", manager)
    monkeypatch.setattr(web, "load_config", lambda: CONFIG)
    web.app.config["TESTING"] = True
    yield web.app.test_client(), manager
    manager.shutdown()


def fake_steps(monkeypatch, step):
    real = web.build_steps

    def build(kind, options, config):
        real(kind, options, config)  # keep the real validation
        return [step]

    monkeypatch.setattr(web, "build_steps", build)


def test_create_and_poll_a_job(client, monkeypatch):
    http, manager = client
    fake_steps(monkeypatch, PROGRESS_SCRIPT)

    response = http.post("/api/jobs", json={"kind": "summarize", "options": {"dry_run": True}})
    assert response.status_code == 202
    job_id = response.get_json()["id"]
    assert manager.get(job_id).done.wait(WAIT)

    data = http.get(f"/api/jobs/{job_id}?since=0").get_json()
    assert data["status"] == "succeeded"
    assert data["options"] == {"dry_run": True}
    assert data["log_next"] == len(data["log"])
    assert http.get(f"/api/jobs/{job_id}?since={data['log_next']}").get_json()["log"] == []

    listing = http.get("/api/jobs").get_json()
    assert listing["active"] is None
    assert listing["jobs"][0]["id"] == job_id
    assert "log" not in listing["jobs"][0]


@pytest.mark.parametrize(
    "body",
    [{}, {"kind": "nope"}, {"kind": "summarize", "options": {"limit": -1}}, {"kind": "filter", "options": {"x": 1}}],
)
def test_bad_job_requests_return_400(client, body):
    http, manager = client
    assert http.post("/api/jobs", json=body).status_code == 400
    assert manager.list() == []


def test_second_job_and_sync_runs_get_409_while_busy(client, monkeypatch):
    http, manager = client
    fake_steps(monkeypatch, SLEEP_SCRIPT)
    job_id = http.post("/api/jobs", json={"kind": "summarize"}).get_json()["id"]

    second = http.post("/api/jobs", json={"kind": "filter"})
    assert second.status_code == 409
    assert second.get_json()["active"] == job_id
    assert http.post("/api/run/filter").status_code == 409
    assert http.post("/api/run/summarize", json={"dry_run": True}).status_code == 409
    assert http.get("/api/jobs").get_json()["active"] == job_id

    assert http.post(f"/api/jobs/{job_id}/cancel").status_code == 200
    assert manager.get(job_id).done.wait(WAIT)
    assert http.get(f"/api/jobs/{job_id}").get_json()["status"] == "cancelled"


def test_unknown_job_is_404(client):
    http, _ = client
    assert http.get("/api/jobs/nope").status_code == 404
    assert http.post("/api/jobs/nope/cancel").status_code == 404


# --- End to end ----------------------------------------------------------------

def test_real_pipeline_dry_run_in_a_scratch_home(monkeypatch, tmp_path):
    """filter -> summarize --dry-run through `python -m`, with a throwaway BASE_DIR."""
    (tmp_path / "data").mkdir()
    shutil.copy(REPO_ROOT / "taxonomy.yml", tmp_path / "taxonomy.yml")
    pd.DataFrame(
        {"업체명": ["알파", "베타", "감마"], "소재지": ["서울특별시 강남구", "부산광역시", "서울특별시 중구"]}
    ).to_csv(tmp_path / "data" / "2025_전문연구요원_인원배정.csv", index=False)
    monkeypatch.setenv("FIRM_ANALYZER_HOME", str(tmp_path))

    manager = JobManager(cwd=tmp_path)
    steps = build_steps("pipeline", {"dry_run": True, "limit": 5}, CONFIG)
    job = run_to_end(manager, steps, kind="pipeline")
    data = job.to_dict(since=0)

    assert data["status"] == "succeeded", "\n".join(data["log"])
    assert "Filtered 2 firms." in data["log"]
    assert data["progress"] == {"current": 2, "total": 2}
    assert data["summary"].startswith("Summary: ")
    assert (tmp_path / "data" / "filtered_firms.csv").exists()
