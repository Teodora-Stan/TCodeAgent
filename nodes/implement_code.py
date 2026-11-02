"""
NOD: implement_code (Faza 3)

Scrie sau modifică `solution.py`. Nodul are trei moduri de lucru, deduse din stare:

  NEW     - încă nu există cod                 -> implementare de la zero
  FIX     - ultima rulare a avut teste picate  -> repară pe baza erorilor pytest
  REFINE  - testele au trecut, dar criticul
            de cod a cerut îmbunătățiri        -> refactorizare fără a strica testele

În modurile FIX și REFINE îi dăm LLM-ului TOT codul curent (pentru un singur
modul e mic, iar bug-urile sunt în corpul funcțiilor, nu în semnături).
"""

from enum import StrEnum

from llm import ask_code
from nodes.common import log_step, task_context
from state import AgentState
from utils.sandbox import SOLUTION_FILE, TEST_FILE
from utils.text import bullet_list, code_block, join_sections, section

SYSTEM_PROMPT = f"""\
Ești un programator Python senior. Scrii modulul `{SOLUTION_FILE}`, testat de `{TEST_FILE}`.
Reguli:
- Respectă EXACT interfața importată de teste.
- Cod clar și modular: funcții mici, type hints, docstring-uri scurte, fără cod duplicat.
- Doar biblioteca standard Python, dacă task-ul nu cere altceva.
- NU modifica testele și nu adapta codul la teste în mod artificial (fără cazuri hardcodate).
- Când repari, schimbă doar ce e necesar și păstrează ce funcționează deja.
Răspunde DOAR cu fișierul complet `{SOLUTION_FILE}`, într-un singur bloc ```python```."""


class Mode(StrEnum):
    """Ce fel de implementare facem în iterația curentă."""

    NEW = "implementare nouă"
    FIX = "reparare teste picate"
    REFINE = "îmbunătățire cerută de critic"


def node_implement_code(state: AgentState) -> dict:
    """Generează o nouă versiune a codului."""
    mode = detect_mode(state)
    code = ask_code(SYSTEM_PROMPT, build_prompt(state, mode))
    iteration = state["code_iterations"] + 1

    return {
        "code": code,
        "code_iterations": iteration,
        "history": log_step(f"Cod v{iteration} ({mode})."),
    }


def detect_mode(state: AgentState) -> Mode:
    """Deduce modul de lucru din stare (vezi docstring-ul modulului)."""
    if not state["code"]:
        return Mode.NEW
    if not state["execution_passed"]:
        return Mode.FIX
    return Mode.REFINE


def build_prompt(state: AgentState, mode: Mode) -> str:
    """Prompt-ul de bază (task + teste) plus secțiunea specifică modului."""
    return join_sections(
        task_context(state),
        section(f"Testele ({TEST_FILE})", code_block(state["test_code"])),
        mode_section(state, mode),
    )


def mode_section(state: AgentState, mode: Mode) -> str | None:
    """Informațiile suplimentare de care are nevoie fiecare mod."""
    if mode == Mode.NEW:
        return None

    current_code = section(f"Codul curent ({SOLUTION_FILE})", code_block(state["code"]))

    if mode == Mode.FIX:
        return join_sections(
            current_code,
            section("Teste picate", bullet_list(state["failing_tests"])),
            section("Output pytest", code_block(state["execution_output"], language="text")),
            # Diagnosticul (dacă a rulat) explică DE CE a picat fiecare test.
            section("Diagnosticul eșecurilor", state["failure_diagnosis"])
            if state["failure_diagnosis"]
            else None,
            section("Sarcina", "Repară codul astfel încât TOATE testele să treacă."),
        )

    # Mode.REFINE
    return join_sections(
        current_code,
        section("Observațiile criticului de cod", state["code_judge_feedback"]),
        section("Sarcina", "Aplică observațiile fără să strici testele care trec deja."),
    )
