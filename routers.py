"""
Routerele = muchiile condiționate ale grafului.

Un router primește starea și întoarce NUMELE nodului următor. Routerele doar
CITESC starea (nu o modifică); toate contoarele sunt actualizate în noduri.
"""

from config import SETTINGS
from node_names import Node
from state import AgentState
from utils.sandbox import CODE_LEVEL_ERRORS

# ---------------------------------------------------------------- Faza 1


def route_after_confirm(state: AgentState) -> Node:
    """Utilizatorul a confirmat -> teste; altfel -> reformulăm cu precizările lui."""
    return Node.GENERATE_TESTS if state["user_confirmed_task"] else Node.CLARIFY_TASK


# ---------------------------------------------------------------- Faza 2


def route_after_generate_tests(state: AgentState) -> Node:
    """Prima generare -> întrebăm de corner cases; regenerările -> direct la critic."""
    return Node.JUDGE_TESTS if state["corner_cases_asked"] else Node.ASK_CORNER_CASES


def route_after_corner_cases(state: AgentState) -> Node:
    """Utilizatorul a dat idei -> le adăugăm în teste; altfel -> criticul de teste."""
    return Node.GENERATE_TESTS if state["user_corner_cases"] else Node.JUDGE_TESTS


def route_after_test_judge(state: AgentState) -> Node:
    """Aprobat -> implementare; respins de prea multe ori -> utilizatorul; altfel -> regenerare."""
    if state["test_judge_passed"]:
        return Node.IMPLEMENT_CODE
    if state["test_judge_iterations"] >= SETTINGS.max_test_judge_iterations:
        return Node.USER_MANUAL_TESTS
    return Node.GENERATE_TESTS


def route_after_manual_tests(state: AgentState) -> Node:
    """Testele lipite au erori de sintaxă -> mai întrebăm o dată; altfel -> implementare."""
    return Node.USER_MANUAL_TESTS if state["manual_tests_error"] else Node.IMPLEMENT_CODE


# ---------------------------------------------------------------- Faza 3


def route_after_execution(state: AgentState) -> Node:
    """Teste verzi -> criticul de cod; agent blocat -> raport (oprire);
    altfel -> diagnostic (cine e de vină?) sau direct reparare."""
    if state["execution_passed"]:
        return Node.JUDGE_CODE
    if is_stuck(state):
        return Node.FINAL_REPORT
    if can_diagnose(state):
        return Node.DIAGNOSE_FAILURE
    return Node.IMPLEMENT_CODE


def can_diagnose(state: AgentState) -> bool:
    """Are sens să întrebăm "e de vină testul?" doar dacă:
    - au picat teste REALE (nu o eroare de import / timeout, care țin sigur de cod), și
    - nu am epuizat numărul de corectări ale testelor.
    """
    only_real_failures = not CODE_LEVEL_ERRORS.intersection(state["failing_tests"])
    repairs_left = state["test_repairs"] < SETTINGS.max_test_repairs
    return only_real_failures and repairs_left


def is_stuck(state: AgentState) -> bool:
    """Agentul e "blocat" dacă:
    - a depășit numărul total de rulări picate, SAU
    - același test a picat de prea multe ori la rând (nu reușește să-l repare).
    """
    too_many_failures = state["failed_runs"] >= SETTINGS.max_fix_attempts
    worst_streak = max(state["failing_streaks"].values(), default=0)
    return too_many_failures or worst_streak >= SETTINGS.max_same_test_failures


def route_after_diagnosis(state: AgentState) -> Node:
    """Teste suspectate ca greșite -> întrebăm utilizatorul; altfel -> reparăm codul."""
    return Node.CONFIRM_TEST_FIX if state["suspect_tests"] else Node.IMPLEMENT_CODE


def route_after_test_fix_confirm(state: AgentState) -> Node:
    """Utilizatorul a aprobat -> corectăm testele; altfel -> reparăm codul."""
    return Node.REPAIR_TESTS if state["test_fix_approved"] else Node.IMPLEMENT_CODE


def route_after_code_judge(state: AgentState) -> Node:
    """Aprobat sau epuizat rundele de îmbunătățire -> raport; altfel -> îmbunătățire."""
    if state["code_judge_passed"]:
        return Node.FINAL_REPORT
    # `refine_iterations` = a câta cerere de îmbunătățire e aceasta (vezi judge_code).
    if state["refine_iterations"] > SETTINGS.max_refine_iterations:
        return Node.FINAL_REPORT
    return Node.IMPLEMENT_CODE
