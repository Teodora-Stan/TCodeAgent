"""
Running the tests against the generated code, in an isolated temporary directory.

WARNING: "sandbox" here only means a temporary directory + a timeout. The
LLM-generated code runs with your user's permissions. Real isolation would
need a container (Docker) or a dedicated sandbox.

File convention (the prompts know it too):
    solution.py       <- the implemented code
    test_solution.py  <- the tests, which do `from solution import ...`
"""

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from utils.text import truncate

SOLUTION_FILE = "solution.py"
TEST_FILE = "test_solution.py"
JUNIT_REPORT = "report.xml"

# "Test name" used when pytest can't even import the files
# (e.g. a syntax error in solution.py), so no real test runs.
COLLECTION_ERROR = "<eroare la import/colectare>"
# "Test name" used when the run exceeded the timeout.
TIMEOUT_ERROR = "<timeout>"

# Failures that are always the code's fault (not a specific test's), so it
# makes no sense to ask "is the test at fault?".
CODE_LEVEL_ERRORS = {COLLECTION_ERROR, TIMEOUT_ERROR}


@dataclass
class TestRunResult:
    """The result of a pytest run."""

    passed: bool                                       # did ALL tests pass?
    failed_tests: list[str] = field(default_factory=list)  # names of the failing tests
    total: int = 0                                     # how many tests ran
    output: str = ""                                   # the pytest output (truncated)


def run_tests(code: str, test_code: str, timeout: int) -> TestRunResult:
    """Writes the code + tests into a temporary directory and runs pytest."""
    with tempfile.TemporaryDirectory(prefix="agent_sandbox_") as tmp:
        workdir = Path(tmp)
        _write_files(workdir, code, test_code)

        try:
            process = _run_pytest(workdir, timeout)
        except subprocess.TimeoutExpired:
            return TestRunResult(
                passed=False,
                failed_tests=[TIMEOUT_ERROR],
                output=f"Testele au depășit {timeout}s (posibilă buclă infinită).",
            )

        total, failed = _parse_junit_report(workdir / JUNIT_REPORT)
        output = truncate(process.stdout + process.stderr)

    # Exit code 0 = all tests passed. Anything else (failing tests,
    # import error, no tests found) counts as a failure.
    passed = process.returncode == 0 and total > 0
    if not passed and not failed:
        # E.g. pytest stopped before writing the report.
        failed = [COLLECTION_ERROR]
    return TestRunResult(passed=passed, failed_tests=failed, total=total, output=output)


def _write_files(workdir: Path, code: str, test_code: str) -> None:
    """Creates solution.py and test_solution.py in the working directory."""
    (workdir / SOLUTION_FILE).write_text(code, encoding="utf-8")
    (workdir / TEST_FILE).write_text(test_code, encoding="utf-8")


def _run_pytest(workdir: Path, timeout: int) -> subprocess.CompletedProcess:
    """Runs pytest as a subprocess (with the same Python interpreter as the agent).

    `--junitxml` produces an XML report from which we extract exactly which tests
    failed, more reliably than parsing the printed text.
    """
    command = [
        sys.executable, "-m", "pytest", TEST_FILE,
        "-q",                       # compact output
        "--tb=short",               # short tracebacks (they fit in the prompt)
        "-p", "no:cacheprovider",   # no .pytest_cache in the temporary directory
        f"--junitxml={JUNIT_REPORT}",
    ]
    return subprocess.run(
        command, cwd=workdir, capture_output=True, text=True, timeout=timeout
    )


def _parse_junit_report(report_path: Path) -> tuple[int, list[str]]:
    """Reads the JUnit report: (total number of tests, list of failing tests)."""
    if not report_path.exists():
        return 0, []

    testcases = ET.parse(report_path).getroot().iter("testcase")
    total, failed = 0, []
    for case in testcases:
        # On an import error, pytest reports a fake "test" named after the
        # file (e.g. "test_solution"). It's not a real test, so we don't count it.
        error = case.find("error")
        if error is not None and error.get("message") == "collection failure":
            failed.append(COLLECTION_ERROR)
            continue

        total += 1
        # A test failed if it has a <failure> child (assert) or an <error> child (exception).
        if case.find("failure") is not None or case.find("error") is not None:
            failed.append(case.get("name", "?"))
    return total, failed
