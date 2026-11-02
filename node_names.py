"""
The names of the graph's nodes, in one place.

`StrEnum` = an enum whose values are also strings. We use `Node.JUDGE_TESTS`
instead of "judge_tests" so typos are caught right in the editor.
"""

from enum import StrEnum


class Node(StrEnum):
    # Phase 1: Clarification & confirmation
    CLARIFY_TASK = "clarify_task"
    USER_CONFIRM = "user_confirm"

    # Phase 2: Tests
    GENERATE_TESTS = "generate_tests"
    ASK_CORNER_CASES = "ask_corner_cases"
    JUDGE_TESTS = "judge_tests"
    USER_MANUAL_TESTS = "user_manual_tests"

    # Phase 3: Implementation & execution
    IMPLEMENT_CODE = "implement_code"
    EXECUTE_TESTS = "execute_tests"
    JUDGE_CODE = "judge_code"

    # Phase 3b: Is the code or the test at fault?
    DIAGNOSE_FAILURE = "diagnose_failure"
    CONFIRM_TEST_FIX = "confirm_test_fix"
    REPAIR_TESTS = "repair_tests"

    # Phase 4: Report
    FINAL_REPORT = "final_report"
