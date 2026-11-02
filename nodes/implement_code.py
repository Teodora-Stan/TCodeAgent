"""
NODE: implement_code (Phase 3)

Writes or modifies `solution.py`. The node has three working modes, inferred from the state:

  NEW     - there is no code yet               -> implementation from scratch
  FIX     - the last run had failing tests     -> fix based on the pytest errors
  REFINE  - the tests passed, but the code
            critic asked for improvements      -> refactor without breaking the tests

In FIX and REFINE modes we give the LLM ALL of the current code (for a single
module it's small, and the bugs are in the function bodies, not in the signatures).
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
    """What kind of implementation we do in the current iteration."""

    NEW = "implementare nouă"
    FIX = "reparare teste picate"
    REFINE = "îmbunătățire cerută de critic"


def node_implement_code(state: AgentState) -> dict:
    """Generates a new version of the code."""
    mode = detect_mode(state)
    code = ask_code(SYSTEM_PROMPT, build_prompt(state, mode))
    iteration = state["code_iterations"] + 1

    return {
        "code": code,
        "code_iterations": iteration,
        "history": log_step(f"Cod v{iteration} ({mode})."),
    }


def detect_mode(state: AgentState) -> Mode:
    """Infers the working mode from the state (see the module docstring)."""
    if not state["code"]:
        return Mode.NEW
    if not state["execution_passed"]:
        return Mode.FIX
    return Mode.REFINE


def build_prompt(state: AgentState, mode: Mode) -> str:
    """The base prompt (task + tests) plus the mode-specific section."""
    return join_sections(
        task_context(state),
        section(f"Testele ({TEST_FILE})", code_block(state["test_code"])),
        mode_section(state, mode),
    )


def mode_section(state: AgentState, mode: Mode) -> str | None:
    """The extra information each mode needs."""
    if mode == Mode.NEW:
        return None

    current_code = section(f"Codul curent ({SOLUTION_FILE})", code_block(state["code"]))

    if mode == Mode.FIX:
        return join_sections(
            current_code,
            section("Teste picate", bullet_list(state["failing_tests"])),
            section("Output pytest", code_block(state["execution_output"], language="text")),
            # The diagnosis (if it ran) explains WHY each test failed.
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
