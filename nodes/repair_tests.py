"""
NOD: repair_tests (Faza 3b)

Corectează DOAR testele aprobate de utilizator, apoi graful rulează din nou
testele pe ACELAȘI cod (muchie fixă repair_tests -> execute_tests). Dacă
diagnosticul a fost corect, testul reparat trece fără să atingem codul.
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
    """Rescrie testele suspectate și păstrează restul suitei."""
    repaired = ask_code(SYSTEM_PROMPT, build_prompt(state))
    repairs = state["test_repairs"] + 1

    # Dacă LLM-ul a produs un fișier invalid, păstrăm testele vechi:
    # mai bine reparăm codul decât să rulăm o suită care nici nu se importă.
    error = syntax_error(repaired)
    if error:
        return {
            "test_repairs": repairs,
            "history": log_step(f"Corectarea testelor a eșuat (sintaxă: {error}); păstrez suita veche."),
        }

    return {
        "test_code": repaired,
        "test_repairs": repairs,
        # Rularea anterioară a picat din cauza testelor, nu a codului -> nu o numărăm.
        "failed_runs": max(0, state["failed_runs"] - 1),
        "failing_streaks": {},
        "history": log_step(f"Am corectat {len(state['suspect_tests'])} teste; rulez din nou."),
    }


def build_prompt(state: AgentState) -> str:
    """Cerința + suita curentă + ce trebuie corectat (+ indicațiile utilizatorului)."""
    return join_sections(
        task_context(state),
        section(f"Suita curentă ({TEST_FILE})", code_block(state["test_code"])),
        section("Teste de corectat (aprobate de utilizator)", bullet_list(state["suspect_tests"])),
        section("Indicațiile utilizatorului", state["test_fix_guidance"])
        if state["test_fix_guidance"]
        else None,
    )
