"""
NODE: repair_tests (Phase 3b)

Corrects ONLY the tests approved by the user, then the graph re-runs the tests
against the SAME code (fixed edge repair_tests -> execute_tests). If the
diagnosis was right, the repaired test passes without touching the code.
"""

from llm import ask_code
from nodes.common import log_step, task_context
from state import AgentState
from utils.sandbox import TEST_FILE
from utils.text import bullet_list, code_block, join_sections, section, syntax_error

SYSTEM_PROMPT = f"""\
Corectezi fișierul de teste `{TEST_FILE}`.
- Modifică DOAR testele / cazurile parametrizate indicate; restul fișierului rămâne identic.
- Verifică pas cu pas fiecare valoare așteptată nouă, pornind de la cerință.
- Dacă un caz nu poate fi corectat sigur, șterge-l în loc să ghicești.
Răspunde DOAR cu fișierul complet de teste, într-un singur bloc ```python```."""


def node_repair_tests(state: AgentState) -> dict:
    """Rewrites the suspected tests and keeps the rest of the suite."""
    repaired = ask_code(SYSTEM_PROMPT, build_prompt(state))
    repairs = state["test_repairs"] + 1

    # If the LLM produced an invalid file, we keep the old tests:
    # better to fix the code than to run a suite that won't even import.
    error = syntax_error(repaired)
    if error:
        return {
            "test_repairs": repairs,
            "history": log_step(f"Corectarea testelor a eșuat (sintaxă: {error}); păstrez suita veche."),
        }

    return {
        "test_code": repaired,
        "test_repairs": repairs,
        # The previous run failed because of the tests, not the code -> we don't count it.
        "failed_runs": max(0, state["failed_runs"] - 1),
        "failing_streaks": {},
        "history": log_step(f"Am corectat {len(state['suspect_tests'])} teste; rulez din nou."),
    }


def build_prompt(state: AgentState) -> str:
    """The request + the current suite + what needs correcting (+ the user's guidance)."""
    return join_sections(
        task_context(state),
        section(f"Suita curentă ({TEST_FILE})", code_block(state["test_code"])),
        section("Teste de corectat (aprobate de utilizator)", bullet_list(state["suspect_tests"])),
        section("Indicațiile utilizatorului", state["test_fix_guidance"])
        if state["test_fix_guidance"]
        else None,
    )
