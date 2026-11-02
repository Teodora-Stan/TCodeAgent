"""
Routers = the graph's conditional edges.

A router receives the state and returns the NAME of the next node. Routers only
READ the state (they don't modify it); all counters are updated inside the nodes.
"""

from config import SETTINGS
from node_names import Node
from state import AgentState
from utils.sandbox import CODE_LEVEL_ERRORS

# ---------------------------------------------------------------- Phase 1


def route_after_confirm(state: AgentState) -> Node:
    """User confirmed -> tests; otherwise -> rephrase using the user's clarifications."""
    return Node.GENERATE_TESTS if state["user_confirmed_task"] else Node.CLARIFY_TASK


# ---------------------------------------------------------------- Phase 2


def route_after_generate_tests(state: AgentState) -> Node:
    """First generation -> ask for corner cases; regenerations -> straight to the critic."""
    return Node.JUDGE_TESTS if state["corner_cases_asked"] else Node.ASK_CORNER_CASES


def route_after_corner_cases(state: AgentState) -> Node:
    """The user gave ideas -> add them to the tests; otherwise -> the test critic."""
    return Node.GENERATE_TESTS if state["user_corner_cases"] else Node.JUDGE_TESTS


def route_after_test_judge(state: AgentState) -> Node:
    """Approved -> implementation; rejected too many times -> the user; otherwise -> regenerate."""
    if state["test_judge_passed"]:
        return Node.IMPLEMENT_CODE
    if state["test_judge_iterations"] >= SETTINGS.max_test_judge_iterations:
        return Node.USER_MANUAL_TESTS
    return Node.GENERATE_TESTS


def route_after_manual_tests(state: AgentState) -> Node:
    """The pasted tests have syntax errors -> ask again; otherwise -> implementation."""
    return Node.USER_MANUAL_TESTS if state["manual_tests_error"] else Node.IMPLEMENT_CODE


# ---------------------------------------------------------------- Phase 3


def route_after_execution(state: AgentState) -> Node:
    """Green tests -> the code critic; agent stuck -> report (stop);
    otherwise -> diagnosis (who is at fault?) or a direct fix."""
    if state["execution_passed"]:
        return Node.JUDGE_CODE
    if is_stuck(state):
        return Node.FINAL_REPORT
    if can_diagnose(state):
        return Node.DIAGNOSE_FAILURE
    return Node.IMPLEMENT_CODE


def can_diagnose(state: AgentState) -> bool:
    """Asking "is the test at fault?" only makes sense if:
    - REAL tests failed (not an import error / timeout, which are always the code's fault), and
    - we haven't used up the allowed number of test corrections.
    """
    only_real_failures = not CODE_LEVEL_ERRORS.intersection(state["failing_tests"])
    repairs_left = state["test_repairs"] < SETTINGS.max_test_repairs
    return only_real_failures and repairs_left


def is_stuck(state: AgentState) -> bool:
    """The agent is "stuck" if:
    - it exceeded the total number of failed runs, OR
    - the same test failed too many times in a row (it can't manage to fix it).
    """
    too_many_failures = state["failed_runs"] >= SETTINGS.max_fix_attempts
    worst_streak = max(state["failing_streaks"].values(), default=0)
    return too_many_failures or worst_streak >= SETTINGS.max_same_test_failures


def route_after_diagnosis(state: AgentState) -> Node:
    """Tests suspected to be wrong -> ask the user; otherwise -> fix the code."""
    return Node.CONFIRM_TEST_FIX if state["suspect_tests"] else Node.IMPLEMENT_CODE


def route_after_test_fix_confirm(state: AgentState) -> Node:
    """The user approved -> correct the tests; otherwise -> fix the code."""
    return Node.REPAIR_TESTS if state["test_fix_approved"] else Node.IMPLEMENT_CODE


def route_after_code_judge(state: AgentState) -> Node:
    """Approved or out of improvement rounds -> report; otherwise -> improve."""
    if state["code_judge_passed"]:
        return Node.FINAL_REPORT
    # `refine_iterations` = which improvement request this is (see judge_code).
    if state["refine_iterations"] > SETTINGS.max_refine_iterations:
        return Node.FINAL_REPORT
    return Node.IMPLEMENT_CODE
