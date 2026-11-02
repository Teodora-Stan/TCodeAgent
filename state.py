"""
The agent's state (AgentState) = the "memory" that flows through the graph.

Each node receives the full state and returns ONLY the fields it changes
(a partial dict). LangGraph then merges it into the global state.

Fields marked with `Annotated[list, operator.add]` have a *reducer*: instead of
being overwritten, the values returned by nodes are APPENDED to the existing list.
That's how we keep the history without copying it by hand in every node.
"""

import operator
from typing import Annotated, Optional, TypedDict


class AgentState(TypedDict):
    # ------------------------------------------------------------------ Phase 1
    task: str                                   # the user's original request
    clarification: str                          # how the agent understood the task (displayable text)
    clarification_history: Annotated[list[str], operator.add]  # the user's feedback, in order
    user_confirmed_task: bool                   # did the user say "ok"?

    # ------------------------------------------------------------------ Phase 2
    test_code: str                              # the pytest suite (full file)
    test_generations: int                       # how many times the suite was (re)generated
    corner_cases_asked: bool                    # have we already asked the user for corner cases?
    user_corner_cases: str                      # the user's ideas ("" = nothing added)
    test_judge_iterations: int                  # how many times the critic evaluated the tests
    test_judge_passed: bool                     # did the critic approve the tests?
    test_judge_feedback: str                    # what the critic is missing (shown to the user)
    manual_tests_error: Optional[str]           # syntax error in the manually written tests

    # ------------------------------------------------------------------ Phase 3
    code: str                                   # the current source code (solution.py)
    code_iterations: int                        # how many code versions were generated (total)
    last_passing_code: str                      # the last version that passed ALL tests

    execution_passed: bool                      # last run: did all tests pass?
    execution_output: str                       # the (truncated) pytest output of the last run
    failing_tests: list[str]                    # the tests that failed in the last run
    failing_streaks: dict[str, int]             # test -> how many times it failed CONSECUTIVELY
    failed_runs: int                            # how many runs had at least one failing test

    failure_diagnosis: str                      # why the tests failed (after diagnose_failure)
    suspect_tests: list[str]                    # tests the LLM believes are wrong (with reason)
    test_fix_approved: bool                     # did the user approve correcting the tests?
    test_fix_guidance: str                      # the user's guidance for the correction
    test_repairs: int                           # how many times the tests were corrected

    code_judge_passed: bool                     # did the code critic approve?
    code_judge_feedback: str                    # the code critic's remarks
    refine_iterations: int                      # how many improvement rounds the critic requested

    # ------------------------------------------------------------------ Phase 4
    final_report: str                           # the final report (markdown)
    history: Annotated[list[str], operator.add] # short log of what happened at each step


def initial_state(task: str) -> AgentState:
    """The starting state for a new task (all counters at zero)."""
    return {
        "task": task,
        "clarification": "",
        "clarification_history": [],
        "user_confirmed_task": False,
        "test_code": "",
        "test_generations": 0,
        "corner_cases_asked": False,
        "user_corner_cases": "",
        "test_judge_iterations": 0,
        "test_judge_passed": False,
        "test_judge_feedback": "",
        "manual_tests_error": None,
        "code": "",
        "code_iterations": 0,
        "last_passing_code": "",
        "execution_passed": False,
        "execution_output": "",
        "failing_tests": [],
        "failing_streaks": {},
        "failed_runs": 0,
        "failure_diagnosis": "",
        "suspect_tests": [],
        "test_fix_approved": False,
        "test_fix_guidance": "",
        "test_repairs": 0,
        "code_judge_passed": False,
        "code_judge_feedback": "",
        "refine_iterations": 0,
        "final_report": "",
        "history": [],
    }
