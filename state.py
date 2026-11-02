"""
Starea agentului (AgentState) = "memoria" care circulă prin graf.

Fiecare nod primește starea completă și întoarce DOAR câmpurile pe care le
modifică (un dict parțial). LangGraph face apoi merge-ul în starea globală.

Câmpurile marcate cu `Annotated[list, operator.add]` au un *reducer*: în loc să
fie suprascrise, valorile întoarse de noduri sunt ADĂUGATE la lista existentă.
Așa păstrăm istoricul fără să-l copiem manual în fiecare nod.
"""

import operator
from typing import Annotated, Optional, TypedDict


class AgentState(TypedDict):
    # ------------------------------------------------------------------ Faza 1
    task: str                                   # cerința originală a utilizatorului
    clarification: str                          # cum a înțeles agentul task-ul (text afișabil)
    clarification_history: Annotated[list[str], operator.add]  # feedback-ul utilizatorului, în ordine
    user_confirmed_task: bool                   # utilizatorul a zis "ok"?

    # ------------------------------------------------------------------ Faza 2
    test_code: str                              # suita de teste pytest (fișier complet)
    test_generations: int                       # de câte ori s-a (re)generat suita
    corner_cases_asked: bool                    # am întrebat deja utilizatorul de corner cases?
    user_corner_cases: str                      # ideile utilizatorului ("" = n-a adăugat nimic)
    test_judge_iterations: int                  # de câte ori a evaluat criticul testele
    test_judge_passed: bool                     # criticul a aprobat testele?
    test_judge_feedback: str                    # ce îi lipsește criticului (afișat utilizatorului)
    manual_tests_error: Optional[str]           # eroare de sintaxă în testele scrise manual

    # ------------------------------------------------------------------ Faza 3
    code: str                                   # codul sursă curent (solution.py)
    code_iterations: int                        # câte versiuni de cod au fost generate (total)
    last_passing_code: str                      # ultima versiune care a trecut TOATE testele

    execution_passed: bool                      # ultima rulare: au trecut toate testele?
    execution_output: str                       # output-ul pytest (trunchiat) al ultimei rulări
    failing_tests: list[str]                    # testele picate la ultima rulare
    failing_streaks: dict[str, int]             # test -> de câte ori a picat CONSECUTIV
    failed_runs: int                            # câte rulări au avut cel puțin un test picat

    failure_diagnosis: str                      # de ce au picat testele (după diagnose_failure)
    suspect_tests: list[str]                    # testele pe care LLM-ul le crede greșite (cu motiv)
    test_fix_approved: bool                     # utilizatorul a aprobat corectarea testelor?
    test_fix_guidance: str                      # precizările utilizatorului pentru corectare
    test_repairs: int                           # de câte ori au fost corectate testele

    code_judge_passed: bool                     # criticul de cod a aprobat?
    code_judge_feedback: str                    # observațiile criticului de cod
    refine_iterations: int                      # câte runde de îmbunătățire a cerut criticul

    # ------------------------------------------------------------------ Faza 4
    final_report: str                           # raportul final (markdown)
    history: Annotated[list[str], operator.add] # jurnal scurt cu ce s-a întâmplat la fiecare pas


def initial_state(task: str) -> AgentState:
    """Starea de pornire pentru un task nou (toate contoarele la zero)."""
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
