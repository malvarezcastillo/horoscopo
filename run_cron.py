#!/usr/bin/env python3
"""horoscopo cron job with structured reporting."""
import asyncio
import os
import subprocess
import sys

from report import Report

PY = sys.executable


def _run(cmd: str, check: bool = True, timeout: int | None = None,
         env_override: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    return subprocess.run(cmd, shell=True, check=check, timeout=timeout,
                          capture_output=True, text=True, env=env)


def main():
    os.makedirs("logs", exist_ok=True)
    report = Report()

    # Unset CLAUDECODE to allow nested claude CLI invocations
    claude_env = {"CLAUDECODE": ""}

    with report.step("scrape_sources") as step:
        r = _run(f"{PY} sources.py", timeout=600)
        step.detail = r.stdout.strip().split("\n")[-1] if r.stdout else "done"

    with report.step("generate_noise") as step:
        r = _run(f"{PY} -c \"from cosmic_noise import generate_all_noise; n=generate_all_noise(); print(f'Generated noise for {{len(n)}} signs')\"", timeout=60)
        step.detail = r.stdout.strip() if r.stdout else "done"

    with report.step("divine_horoscopes") as step:
        r = _run(f"{PY} diviner.py", timeout=600, env_override=claude_env)
        step.detail = r.stdout.strip().split("\n")[-1] if r.stdout else "done"

    if os.environ.get("TELEGRAM_CHANNEL"):
        with report.step("telegram_publish") as step:
            try:
                r = _run(f"{PY} telegram_publish.py", timeout=120)
                step.detail = r.stdout.strip().split("\n")[-1] if r.stdout else "done"
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                step.warn(f"Non-fatal: {e}")

    with report.step("export_json") as step:
        r = _run(f"{PY} export_json.py", timeout=60)
        step.detail = r.stdout.strip() if r.stdout else "done"

    with report.step("deploy_ghpages") as step:
        deploy_script = os.path.join(os.path.dirname(__file__), "..", "deploy_ghpages.sh")
        r = _run(f'bash "{deploy_script}" docs "Update horoscopo del dia"', timeout=600)
        step.detail = r.stdout.strip().split("\n")[-1] if r.stdout else "deployed"

    report.finish()


if __name__ == "__main__":
    main()
