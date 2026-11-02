"""
NOD: generate_tests (Faza 2)

Generează suita de teste pytest. Se poate ajunge aici din trei locuri:
  1. prima dată, după confirmarea task-ului       -> suită nouă
  2. după ce utilizatorul a dat corner cases      -> suita existentă + cazurile lui
  3. după ce criticul a respins testele           -> suita existentă + ce i-a lipsit criticului

În cazurile 2 și 3 îi dăm LLM-ului suita curentă și îi cerem s-o COMPLETEZE,
nu s-o rescrie de la zero (ca să nu pierdem teste bune).
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
    """Generează sau completează suita de teste."""
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
    """Prompt-ul = contextul task-ului + (opțional) suita existentă, corner cases, critica."""
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
