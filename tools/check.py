"""Run every BearPlans check with one command (standard library only).

    python tools/check.py          # everything, including real-browser (e2e) tests
    python tools/check.py --fast   # skip tests marked e2e (no Chrome needed, much faster)

Steps run in order and stop at the first failure: frontend typecheck, frontend
tests, frontend build, backend tests. Each step prints one summary line; on a
failure the last lines of its output are shown and the full log path is printed.
The exit code is 0 only if every step passed.

The checks never touch real data: BEARPLANS_DATA_DIR points to a new temporary
folder and BEARPLANS_SECRETS_FILE to a file inside it that does not exist.
(An empty BEARPLANS_SECRETS_FILE would not be enough: secrets.py treats an empty
value as unset and falls back to the data folder.)
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
TAIL_LINES = 40


def python_executable() -> str:
    venv = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(venv) if venv.exists() else sys.executable


def npm_executable() -> str:
    npm = shutil.which("npm")
    if npm is None:
        sys.exit("check: npm was not found on PATH; install Node (see README).")
    return npm


def vitest_totals(output: str) -> str:
    match = re.search(r"^\s*Tests\s+(.+?)\s*$", output, re.MULTILINE)
    return match.group(1) if match else ""


def pytest_totals(output: str) -> str:
    pattern = r"^=*\s*\d+ (passed|failed|error|errors|skipped|deselected).* in [\d.]+s"
    lines = [line for line in output.splitlines() if re.match(pattern, line)]
    return lines[-1].strip("= ") if lines else ""


def run_step(name: str, command: list[str], env: dict[str, str], log_dir: Path, totals) -> bool:
    log_path = log_dir / f"{re.sub(r'[^a-z]+', '-', name).strip('-')}.log"
    start = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(
            command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, text=True
        )
    elapsed = time.monotonic() - start
    output = log_path.read_text(encoding="utf-8", errors="replace")
    summary = totals(output) if totals else ""
    status = "PASS" if result.returncode == 0 else f"FAIL (exit {result.returncode})"
    detail = f" — {summary}" if summary else ""
    print(f"{status:<15} {name:<20} {elapsed:7.1f}s{detail}", flush=True)
    if result.returncode != 0:
        lines = output.splitlines()
        failures = [line for line in lines if line.startswith(("FAILED ", "ERROR "))]
        if failures:  # pytest summary lines name each failing test
            print(f"\n--- failing tests in {name} ---")
            print("\n".join(line[:200] for line in failures))
        else:
            print(f"\n--- last {TAIL_LINES} lines of {name} ---")
            print("\n".join(lines[-TAIL_LINES:]))
        print(f"--- full log: {log_path} ---\n")
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fast", action="store_true", help="skip real-browser (e2e) tests")
    args = parser.parse_args(argv)

    scratch = Path(tempfile.mkdtemp(prefix="bearplans-check-"))
    data_dir = scratch / "data"
    data_dir.mkdir()
    log_dir = scratch / "logs"
    log_dir.mkdir()
    env = {
        **os.environ,
        "BEARPLANS_DATA_DIR": str(data_dir),
        "BEARPLANS_SECRETS_FILE": str(scratch / "no-secrets" / "bearplans.secrets.env"),
        "CI": os.environ.get("CI", "1"),  # keeps vitest from entering watch mode
    }

    npm = npm_executable()
    pytest_cmd = [python_executable(), "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    if args.fast:
        pytest_cmd += ["-m", "not e2e"]

    steps = [
        ("frontend typecheck", [npm, "--prefix", str(FRONTEND), "run", "typecheck"], None),
        ("frontend tests", [npm, "--prefix", str(FRONTEND), "test"], vitest_totals),
        ("frontend build", [npm, "--prefix", str(FRONTEND), "run", "build"], None),
        ("backend tests" + (" (fast)" if args.fast else ""), pytest_cmd, pytest_totals),
    ]

    print(f"BearPlans checks ({'fast' if args.fast else 'full'}); disposable data: {data_dir}")
    start = time.monotonic()
    for name, command, totals in steps:
        if not run_step(name, command, env, log_dir, totals):
            print(f"check: FAILED at '{name}' after {time.monotonic() - start:.1f}s")
            return 1
    print(f"check: all {len(steps)} steps passed in {time.monotonic() - start:.1f}s")
    shutil.rmtree(scratch, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
