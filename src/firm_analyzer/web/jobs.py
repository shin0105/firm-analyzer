"""
Background jobs for the pipeline scripts.

A summarize or segment run over the full firm list takes far longer than any
HTTP request should stay open, so the web API starts the script as a
subprocess, returns a job id at once, and lets the UI poll for progress and
log output (and cancel the run).

Design points:

- One pipeline job at a time. filter, summarize and segment all write to the
  same data/ and results directories, so a second concurrent run would race
  the first. `JobManager.start` refuses while a job is active.
- Commands are built only from validated options mapped onto fixed flags;
  no client string reaches the command line except checked ids.
- stdout is the script's own progress output and is returned to the client.
  stderr (tracebacks with absolute paths and possibly key fragments) is only
  logged server-side, matching the synchronous /api/run/* endpoints.
- Progress comes from the `[i/n]` prefix the scripts already print per firm.
- State is in memory: jobs do not survive a server restart, and running
  subprocesses are terminated when the server exits.
"""

from __future__ import annotations

import itertools
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import firm_analyzer
from firm_analyzer.config import BASE_DIR
from firm_analyzer.llm import PROVIDER_IDS

#: Script module per single-step job kind.
MODULES = {
    "filter": "firm_analyzer.core.filter",
    "summarize": "firm_analyzer.core.summarize",
    "segment": "firm_analyzer.core.resegment",
}
JOB_KINDS = ("filter", "summarize", "segment", "pipeline")

#: `Processing [3/120] name...`, `Skipping [4/120] name ...` (summarize) and
#: `[3/120] category/name` (segment).
PROGRESS_LINE = re.compile(r"^(?:Processing |Skipping )?\[(\d+)/(\d+)\]")
#: Lines worth surfacing as the job's one-line result.
SUMMARY_LINE = re.compile(r"^(Summary: |Filtered \d+ firms)")

MAX_LOG_LINES = int(os.getenv("JOB_LOG_LINES", "5000"))
MAX_STDERR_LINES = 200
MAX_JOBS_KEPT = 20
MAX_LIMIT = 100_000
#: Kill a job that runs longer than this. 0 (the default) means no limit:
#: a full summarize run can legitimately take hours.
JOB_TIMEOUT_SECONDS = float(os.getenv("JOB_TIMEOUT_SECONDS", "0"))
CANCEL_GRACE_SECONDS = 10.0

ACTIVE_STATES = ("queued", "running")


class JobError(ValueError):
    """A job request that cannot be run. The message is safe to show users."""


class JobConflict(RuntimeError):
    """Another job is still running."""

    def __init__(self, active: "Job"):
        super().__init__(f"A {active.kind} job is already running.")
        self.active = active


@dataclass
class Step:
    """One script invocation inside a job."""

    name: str
    argv: list


# ---------------------------------------------------------------------------
# Option validation -> commands
# ---------------------------------------------------------------------------

def _check_keys(options: dict, allowed: set) -> None:
    unknown = sorted(set(options) - allowed)
    if unknown:
        raise JobError(f"Unknown option(s): {', '.join(unknown)}")


def _bool(options: dict, key: str, default: bool = False) -> bool:
    value = options.get(key, default)
    if not isinstance(value, bool):
        raise JobError(f"{key} must be true or false")
    return value


def _limit(options: dict) -> Optional[int]:
    value = options.get("limit")
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise JobError("limit must be an integer")
    try:
        limit = int(value)
    except (TypeError, ValueError):
        raise JobError("limit must be an integer") from None
    if not 1 <= limit <= MAX_LIMIT:
        raise JobError(f"limit must be between 1 and {MAX_LIMIT}")
    return limit


def _provider(options: dict) -> Optional[str]:
    value = options.get("provider")
    if value in (None, ""):
        return None
    if value not in PROVIDER_IDS:
        raise JobError("Unknown provider")
    return value


def _module_command(module: str, args: list) -> list:
    # -u: unbuffered, so progress lines arrive as they are printed.
    return [sys.executable, "-u", "-m", module, *args]


def _summarize_args(options: dict) -> list:
    args = []
    if _bool(options, "dry_run"):
        args.append("--dry-run")
    limit = _limit(options)
    if limit:
        args += ["--limit", str(limit)]
    provider = _provider(options)
    if provider:
        args += ["--provider", provider]
    if _bool(options, "no_segmentation"):
        args.append("--no-segmentation")
    return args


SUMMARIZE_OPTIONS = {"dry_run", "limit", "provider", "no_segmentation"}
SEGMENT_OPTIONS = {"dry_run", "limit", "provider", "relocate", "force", "categories"}


def build_steps(kind: Any, options: Any, config: dict) -> list[Step]:
    """Turn a job request into the commands to run, or raise JobError."""
    if kind not in JOB_KINDS:
        raise JobError(f"kind must be one of: {', '.join(JOB_KINDS)}")
    if options is None:
        options = {}
    if not isinstance(options, dict):
        raise JobError("options must be an object")

    if kind == "filter":
        _check_keys(options, set())
        return [Step("filter", _module_command(MODULES["filter"], []))]

    if kind == "summarize":
        _check_keys(options, SUMMARIZE_OPTIONS)
        return [Step("summarize", _module_command(MODULES["summarize"], _summarize_args(options)))]

    if kind == "pipeline":
        _check_keys(options, SUMMARIZE_OPTIONS)
        return [
            Step("filter", _module_command(MODULES["filter"], [])),
            Step("summarize", _module_command(MODULES["summarize"], _summarize_args(options))),
        ]

    # segment
    _check_keys(options, SEGMENT_OPTIONS)
    args = []
    if _bool(options, "dry_run"):
        args.append("--dry-run")
    limit = _limit(options)
    if limit:
        args += ["--limit", str(limit)]
    provider = _provider(options)
    if provider:
        args += ["--provider", provider]
    if _bool(options, "relocate"):
        args.append("--relocate")
    if _bool(options, "force"):
        args.append("--force")
    categories = options.get("categories") or []
    if not isinstance(categories, list) or not all(isinstance(c, str) for c in categories):
        raise JobError("categories must be a list of category ids")
    valid = {c["id"] for c in config.get("categories", []) if c.get("id")}
    unknown = sorted(set(categories) - valid)
    if unknown:
        raise JobError(f"Unknown category: {', '.join(unknown)}")
    for category in categories:
        args += ["--category", category]
    return [Step("segment", _module_command(MODULES["segment"], args))]


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

@dataclass
class Job:
    kind: str
    options: dict
    steps: list
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    step_index: int = 0
    returncode: Optional[int] = None
    error: Optional[str] = None
    progress: Optional[dict] = None
    summary: Optional[str] = None

    def __post_init__(self):
        self._lines: deque = deque(maxlen=MAX_LOG_LINES)
        self._line_count = 0
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self._cancel_reason: Optional[str] = None
        self.done = threading.Event()

    @property
    def active(self) -> bool:
        return self.status in ACTIVE_STATES

    def append(self, line: str) -> None:
        with self._lock:
            self._lines.append(line)
            self._line_count += 1
            match = PROGRESS_LINE.match(line)
            if match:
                self.progress = {"current": int(match.group(1)), "total": int(match.group(2))}
            if SUMMARY_LINE.match(line):
                self.summary = line

    def elapsed(self) -> Optional[float]:
        """Seconds run so far, or in total once finished."""
        if self.started_at is None:
            return None
        return (self.finished_at or time.time()) - self.started_at

    def to_dict(self, since: Optional[int] = None) -> dict:
        """The job as JSON. With `since`, includes log lines from that index on."""
        with self._lock:
            data = {
                "id": self.id,
                "kind": self.kind,
                "options": self.options,
                "status": self.status,
                "steps": [step.name for step in self.steps],
                "step_index": self.step_index,
                "created_at": self.created_at,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "elapsed": self.elapsed(),
                "returncode": self.returncode,
                "error": self.error,
                "progress": self.progress,
                "summary": self.summary,
                "log_lines": self._line_count,
            }
            if since is not None:
                first = self._line_count - len(self._lines)
                start = max(since, first)
                data["log"] = list(itertools.islice(self._lines, start - first, None))
                data["log_start"] = start
                data["log_next"] = self._line_count
                data["log_truncated"] = since < first
            return data


def _subprocess_env() -> dict:
    """Make the package importable for `python -m` and keep output UTF-8."""
    env = dict(os.environ)
    package_root = str(Path(firm_analyzer.__file__).resolve().parent.parent)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = package_root + (os.pathsep + existing if existing else "")
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


class JobManager:
    """Starts, tracks and cancels pipeline jobs. Thread-safe."""

    def __init__(self, cwd: Optional[Path] = None, max_jobs: int = MAX_JOBS_KEPT,
                 timeout: float = JOB_TIMEOUT_SECONDS):
        self._jobs: "OrderedDict[str, Job]" = OrderedDict()
        self._lock = threading.Lock()
        self._cwd = cwd or BASE_DIR
        self._max_jobs = max_jobs
        self._timeout = timeout

    def start(self, kind: str, options: dict, steps: list) -> Job:
        with self._lock:
            active = self._active_locked()
            if active is not None:
                raise JobConflict(active)
            job = Job(kind=kind, options=options, steps=steps)
            self._jobs[job.id] = job
            self._trim_locked()
        threading.Thread(target=self._run, args=(job,), daemon=True, name=f"job-{job.id}").start()
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list:
        """Most recent first."""
        with self._lock:
            return list(reversed(self._jobs.values()))

    def active(self) -> Optional[Job]:
        with self._lock:
            return self._active_locked()

    def cancel(self, job_id: str, reason: str = "Cancelled.") -> Optional[Job]:
        job = self.get(job_id)
        if job is None or not job.active:
            return job
        job._cancel_reason = reason
        proc = job._proc
        if proc is not None and proc.poll() is None:
            proc.terminate()
            threading.Thread(target=self._kill_after_grace, args=(proc,), daemon=True).start()
        return job

    def shutdown(self) -> None:
        """Terminate every running job; registered with atexit by the app."""
        for job in self.list():
            if job.active:
                self.cancel(job.id, "Server shut down.")

    # -- internals ----------------------------------------------------------

    def _active_locked(self) -> Optional[Job]:
        return next((job for job in self._jobs.values() if job.active), None)

    def _trim_locked(self) -> None:
        finished = [jid for jid, job in self._jobs.items() if not job.active]
        while len(self._jobs) > self._max_jobs and finished:
            del self._jobs[finished.pop(0)]

    @staticmethod
    def _kill_after_grace(proc: subprocess.Popen) -> None:
        try:
            proc.wait(timeout=CANCEL_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            proc.kill()

    def _run(self, job: Job) -> None:
        job.status = "running"
        job.started_at = time.time()
        timer = None
        if self._timeout > 0:
            timer = threading.Timer(
                self._timeout, self.cancel, args=(job.id, f"Timed out after {self._timeout:.0f}s.")
            )
            timer.daemon = True
            timer.start()

        try:
            for index, step in enumerate(job.steps):
                if job._cancel_reason:
                    break
                job.step_index = index
                job.progress = None
                job.append(f"▶ {step.name}")
                returncode = self._run_step(job, step)
                job.returncode = returncode
                if returncode != 0:
                    if not job._cancel_reason:
                        job.error = (
                            f"{step.name} failed (exit {returncode}); see the log above "
                            "and the server log for details."
                        )
                    break
        except Exception as exc:  # pragma: no cover - defensive: never leave a job "running"
            print(f"Job {job.id} crashed: {exc!r}", file=sys.stderr)
            job.error = "The job could not be run; see the server log for details."
        finally:
            if timer is not None:
                timer.cancel()
            if job._cancel_reason:
                job.status = "cancelled"
                job.error = job._cancel_reason
            elif job.error:
                job.status = "failed"
            else:
                job.status = "succeeded"
            job.finished_at = time.time()
            job._proc = None
            job.done.set()

    def _run_step(self, job: Job, step: Step) -> int:
        proc = subprocess.Popen(
            step.argv,
            cwd=str(self._cwd),
            env=_subprocess_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        job._proc = proc
        if job._cancel_reason:  # cancelled between steps, before this one was visible
            proc.terminate()

        stderr_tail: deque = deque(maxlen=MAX_STDERR_LINES)
        reader = threading.Thread(
            target=lambda: stderr_tail.extend(proc.stderr), daemon=True
        )
        reader.start()

        assert proc.stdout is not None
        for line in proc.stdout:
            job.append(line.rstrip("\n"))
        returncode = proc.wait()
        reader.join(timeout=5)

        if returncode != 0 and stderr_tail:
            print(
                f"Job {job.id} step {step.name} exited {returncode}. stderr:\n"
                + "".join(stderr_tail),
                file=sys.stderr,
            )
        return returncode
