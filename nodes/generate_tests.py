"""
NODE: generate_tests (Phase 2)

Generates the pytest suite. We can get here from three places:
  1. the first time, after the task is confirmed  -> new suite
  2. after the user gave corner cases             -> existing suite + the user's cases
  3. after the critic rejected the tests          -> existing suite + what the critic was missing

In cases 2 and 3 we give the LLM the current suite and ask it to EXTEND it,
not rewrite it from scratch (so we don't lose good tests).
"""

from llm import ask_code
from nodes.common import log_step, task_context
from state import AgentState
from utils.sandbox import SOLUTION_FILE, TEST_FILE
from utils.text import code_block, join_sections, list_test_names, section

SYSTEM_PROMPT = f"""\
Ești un inginer QA care scrie teste pytest ÎNAINTE ca implementarea să existe (TDD).
Reguli:
- Fișierul de teste se numește `{TEST_FILE}`; codul testat e în `{SOLUTION_FILE}`,
  deci importă cu `from solution import ...` exact interfața confirmată.
- Funcții de test simple (`def test_...`), cu nume descriptive; folosește `pytest.mark.parametrize` unde ajută.
- Acoperă: cazul normal, cazuri limită (input gol, valori extreme, tipuri neașteptate) și erorile așteptate (`pytest.raises`).
- Valorile așteptate trebuie să fie CORECTE - calculează-le cu atenție.
- Teste deterministe: fără rețea, fără fișiere externe, fără timp real.
- Dacă primești o suită existentă, PĂSTREAZĂ testele corecte și adaugă/repară doar ce e necesar.
Răspunde DOAR cu fișierul complet de teste, într-un singur bloc ```python```."""


def node_generate_tests(state: AgentState) -> dict:
    """Generates or extends the test suite."""
    test_code = ask_code(SYSTEM_PROMPT, build_prompt(state))
    generation = state["test_generations"] + 1

    return {
        "test_code": test_code,
        "test_generations": generation,
        "history": log_step(
            f"Suita de teste v{generation}: {len(list_test_names(test_code))} teste."
        ),
    }


def build_prompt(state: AgentState) -> str:
    """The prompt = the task context + (optionally) the existing suite, corner cases, the critique."""
    return join_sections(
        task_context(state),
        section("Suita de teste existentă (de completat)", code_block(state["test_code"]))
        if state["test_code"]
        else None,
        section("Corner cases cerute de utilizator (OBLIGATORIU de acoperit)", state["user_corner_cases"])
        if state["user_corner_cases"]
        else None,
        section("Observațiile criticului de teste (de rezolvat)", state["test_judge_feedback"])
        if state["test_judge_feedback"]
        else None,
    )
