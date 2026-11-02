"""
Rularea testelor pe codul generat, într-un director temporar izolat.

ATENȚIE: "sandbox" aici înseamnă doar un director temporar + timeout. Codul
generat de LLM rulează cu drepturile utilizatorului tău. Pentru izolare reală
ar trebui un container (Docker) sau un sandbox dedicat.

Convenția de fișiere (o cunosc și prompt-urile):
    solution.py       <- codul implementat
    test_solution.py  <- testele, care fac `from solution import ...`
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

# "Nume de test" folosit când pytest nici nu poate importa fișierele
# (ex: eroare de sintaxă în solution.py), deci nu rulează niciun test real.
COLLECTION_ERROR = "<eroare la import/colectare>"
# "Nume de test" folosit când rularea a depășit timeout-ul.
TIMEOUT_ERROR = "<timeout>"

# Eșecuri care țin sigur de cod (nu de un test anume), deci nu are sens
# să întrebăm "e de vină testul?".
CODE_LEVEL_ERRORS = {COLLECTION_ERROR, TIMEOUT_ERROR}


@dataclass
class TestRunResult:
    """Rezultatul unei rulări pytest."""

    passed: bool                                       # TOATE testele au trecut?
    failed_tests: list[str] = field(default_factory=list)  # numele testelor picate
    total: int = 0                                     # câte teste au fost rulate
    output: str = ""                                   # output-ul pytest (trunchiat)


def run_tests(code: str, test_code: str, timeout: int) -> TestRunResult:
    """Scrie codul + testele într-un director temporar și rulează pytest."""
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

    # Cod de ieșire 0 = toate testele au trecut. Orice altceva (teste picate,
    # eroare la import, niciun test găsit) e considerat eșec.
    passed = process.returncode == 0 and total > 0
    if not passed and not failed:
        # Ex: pytest s-a oprit înainte să scrie raportul.
        failed = [COLLECTION_ERROR]
    return TestRunResult(passed=passed, failed_tests=failed, total=total, output=output)


def _write_files(workdir: Path, code: str, test_code: str) -> None:
    """Creează solution.py și test_solution.py în directorul de lucru."""
    (workdir / SOLUTION_FILE).write_text(code, encoding="utf-8")
    (workdir / TEST_FILE).write_text(test_code, encoding="utf-8")


def _run_pytest(workdir: Path, timeout: int) -> subprocess.CompletedProcess:
    """Rulează pytest ca subproces (cu același interpreter Python ca agentul).

    `--junitxml` produce un raport XML din care extragem exact testele picate,
    mai sigur decât să parsăm textul afișat.
    """
    command = [
        sys.executable, "-m", "pytest", TEST_FILE,
        "-q",                       # output compact
        "--tb=short",               # traceback-uri scurte (încap în prompt)
        "-p", "no:cacheprovider",   # fără .pytest_cache în directorul temporar
        f"--junitxml={JUNIT_REPORT}",
    ]
    return subprocess.run(
        command, cwd=workdir, capture_output=True, text=True, timeout=timeout
    )


def _parse_junit_report(report_path: Path) -> tuple[int, list[str]]:
    """Citește raportul JUnit: (număr total de teste, lista testelor picate)."""
    if not report_path.exists():
        return 0, []

    testcases = ET.parse(report_path).getroot().iter("testcase")
    total, failed = 0, []
    for case in testcases:
        # La o eroare de import, pytest raportează un "test" fals numit după
        # fișier (ex: "test_solution"). Nu e un test real, deci nu-l numărăm.
        error = case.find("error")
        if error is not None and error.get("message") == "collection failure":
            failed.append(COLLECTION_ERROR)
            continue

        total += 1
        # Un test e picat dacă are un copil <failure> (assert) sau <error> (excepție).
        if case.find("failure") is not None or case.find("error") is not None:
            failed.append(case.get("name", "?"))
    return total, failed
