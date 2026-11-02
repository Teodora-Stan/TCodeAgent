"""
Numele nodurilor din graf, într-un singur loc.

`StrEnum` = enum ale cărui valori sunt și string-uri. Folosim `Node.JUDGE_TESTS`
în loc de "judge_tests" ca să prindem greșelile de scriere încă din editor.
"""

from enum import StrEnum


class Node(StrEnum):
    # Faza 1: Clarificare & confirmare
    CLARIFY_TASK = "clarify_task"
    USER_CONFIRM = "user_confirm"

    # Faza 2: Teste
    GENERATE_TESTS = "generate_tests"
    ASK_CORNER_CASES = "ask_corner_cases"
    JUDGE_TESTS = "judge_tests"
    USER_MANUAL_TESTS = "user_manual_tests"

    # Faza 3: Implementare & execuție
    IMPLEMENT_CODE = "implement_code"
    EXECUTE_TESTS = "execute_tests"
    JUDGE_CODE = "judge_code"

    # Faza 3b: E de vină codul sau testul?
    DIAGNOSE_FAILURE = "diagnose_failure"
    CONFIRM_TEST_FIX = "confirm_test_fix"
    REPAIR_TESTS = "repair_tests"

    # Faza 4: Raport
    FINAL_REPORT = "final_report"
