"""
NODE: execute_tests (Phase 3, no LLM)

Runs pytest on the current code and updates the statistics the router uses
to decide whether we keep trying or stop:

  - failing_streaks: how many times in a row EACH test failed. If a test fails
    `max_same_test_failures` times consecutively, the agent is "stuck" on it.
  - failed_runs: how many runs failed in total (the global limit).
  - last_passing_code: the last green version, so we don't lose good code if
    an improvement requested by the critic breaks something.
"""

from config import SETTINGS
from nodes.common import log_step
from state import AgentState
from utils.sandbox import run_tests


def node_execute_tests(state: AgentState) -> dict:
    """Runs the tests and updates the state with the results."""
    result = run_tests(state["code"], state["test_code"], SETTINGS.test_timeout_seconds)

    update = {
        "execution_passed": result.passed,
        "execution_output": result.output,
        "failing_tests": result.failed_tests,
        "failing_streaks": update_streaks(state["failing_streaks"], result.failed_tests),
        # The diagnosis belongs to the previous run; diagnose_failure recomputes it when needed.
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
    """The new consecutive-failure streak for each test.

    Tests that NO LONGER fail disappear from the dict (their streak was broken).
    Example: previous={"test_a": 2, "test_b": 1}, failed_now=["test_a"]
             -> {"test_a": 3}
    """
    return {test: previous.get(test, 0) + 1 for test in failed_now}
