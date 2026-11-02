"""
NOD: execute_tests (Faza 3, fără LLM)

Rulează pytest pe codul curent și actualizează statisticile folosite de router
ca să decidă dacă mai încercăm sau ne oprim:

  - failing_streaks: de câte ori la rând a picat FIECARE test. Dacă un test
    pică de `max_same_test_failures` ori consecutiv, agentul e "blocat" pe el.
  - failed_runs: câte rulări au eșuat în total (limita globală).
  - last_passing_code: ultima versiune verde, ca să nu pierdem cod bun dacă o
    îmbunătățire cerută de critic strică ceva.
"""

from config import SETTINGS
from nodes.common import log_step
from state import AgentState
from utils.sandbox import run_tests


def node_execute_tests(state: AgentState) -> dict:
    """Rulează testele și actualizează starea cu rezultatele."""
    result = run_tests(state["code"], state["test_code"], SETTINGS.test_timeout_seconds)

    update = {
        "execution_passed": result.passed,
        "execution_output": result.output,
        "failing_tests": result.failed_tests,
        "failing_streaks": update_streaks(state["failing_streaks"], result.failed_tests),
        # Diagnosticul ține de rularea anterioară; diagnose_failure îl recalculează la nevoie.
        "failure_diagnosis": "",
        "suspect_tests": [],
        "test_fix_approved": False,
    }

    if result.passed:
        update["last_passing_code"] = state["code"]
        update["history"] = log_step(f"Toate cele {result.total} teste au trecut.")
    else:
        update["failed_runs"] = state["failed_runs"] + 1
        update["history"] = log_step(
            f"Au picat {len(result.failed_tests)}/{result.total or '?'} teste: "
            + ", ".join(result.failed_tests[:5])
        )
    return update


def update_streaks(previous: dict[str, int], failed_now: list[str]) -> dict[str, int]:
    """Noua serie de eșecuri consecutive pentru fiecare test.

    Testele care NU mai pică dispar din dicționar (seria lor s-a întrerupt).
    Exemplu: previous={"test_a": 2, "test_b": 1}, failed_now=["test_a"]
             -> {"test_a": 3}
    """
    return {test: previous.get(test, 0) + 1 for test in failed_now}
