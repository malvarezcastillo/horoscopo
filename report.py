"""Structured execution report for scraper orchestrator.

Copy this file into each scraper project. No external dependencies.

Usage:
    from report import Report

    report = Report()
    with report.step("step_name") as step:
        do_work()
        step.detail = "12 new items"
    report.finish()
"""
import json
import os
import signal
import sys
import threading
import time
import traceback
from contextlib import contextmanager
from datetime import datetime


class Step:
    __slots__ = ("name", "status", "started_at", "finished_at",
                 "duration_s", "detail", "error")

    def __init__(self, name: str):
        self.name = name
        self.status = "ok"
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self.finished_at = None
        self.duration_s = None
        self.detail = None
        self.error = None

    def warn(self, reason: str):
        self.status = "warning"
        self.detail = reason

    def skip(self, reason: str = ""):
        self.status = "skipped"
        if reason:
            self.detail = reason
        raise _SkipStep()

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_s": self.duration_s,
        }
        if self.detail:
            d["detail"] = self.detail
        if self.error:
            d["error"] = self.error
        return d


class _SkipStep(Exception):
    pass


class Report:
    def __init__(self, report_dir: str | None = None):
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self.steps: list[Step] = []
        self._lock = threading.Lock()
        self._report_dir = report_dir or os.getcwd()
        self._report_path = os.path.join(self._report_dir, "report.json")
        self._prev_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, self._sigterm_handler)

    @contextmanager
    def step(self, name: str):
        s = Step(name)
        t0 = time.monotonic()
        try:
            yield s
        except _SkipStep:
            pass
        except (SystemExit, KeyboardInterrupt):
            s.duration_s = round(time.monotonic() - t0, 1)
            s.finished_at = datetime.now().isoformat(timespec="seconds")
            if s.status == "ok":
                s.status = "failed"
                s.error = "Interrupted"
            with self._lock:
                self.steps.append(s)
            raise
        except Exception:
            s.status = "failed"
            s.error = traceback.format_exc()[-2000:]
        finally:
            s.duration_s = round(time.monotonic() - t0, 1)
            s.finished_at = datetime.now().isoformat(timespec="seconds")
            with self._lock:
                self.steps.append(s)

    def _derive_status(self) -> str:
        if not self.steps:
            return "failed"
        statuses = {s.status for s in self.steps}
        if statuses <= {"ok", "skipped"}:
            return "success"
        if "failed" not in statuses:
            return "warning"
        if "ok" in statuses:
            return "partial"
        return "failed"

    def _build_summary(self) -> str:
        counts: dict[str, int] = {}
        for s in self.steps:
            counts[s.status] = counts.get(s.status, 0) + 1
        parts = []
        for status in ("ok", "warning", "failed", "skipped"):
            if status in counts:
                parts.append(f"{counts[status]} {status}")
        return ", ".join(parts)

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "status": self._derive_status(),
            "started_at": self.started_at,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "steps": [s.to_dict() for s in self.steps],
            "summary": self._build_summary(),
        }

    def _write(self):
        tmp = self._report_path + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            os.replace(tmp, self._report_path)
        except OSError as e:
            print(f"WARNING: Could not write report.json: {e}", file=sys.stderr)

    def finish(self):
        self._write()
        status = self._derive_status()
        sys.exit(0 if status in ("success", "warning") else 1)

    def _sigterm_handler(self, signum, frame):
        self._write()
        sys.exit(128 + signum)
