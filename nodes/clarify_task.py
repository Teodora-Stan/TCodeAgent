"""
NOD: clarify_task (Faza 1)

Agentul reformulează cerința, propune interfața (semnăturile funcțiilor) și își
declară presupunerile. Rezultatul e arătat utilizatorului în nodul următor
(user_confirm). Dacă utilizatorul nu e de acord, ajungem iar aici, iar feedback-ul
lui apare în prompt prin `task_context` (câmpul `clarification_history`).
"""

from llm import ask_structured
from nodes.common import log_step, task_context
from schemas import TaskUnderstanding
from state import AgentState
from utils.text import bullet_list, join_sections, section

SYSTEM_PROMPT = """\
Ești un inginer software senior care analizează o cerință înainte de a o implementa în Python.
- Reformulează cerința clar și concis.
- Propune interfața publică (funcții / clase cu type hints). Totul va fi într-un singur modul `solution.py`.
- Notează explicit presupunerile acolo unde cerința e ambiguă.
- Dacă utilizatorul a dat precizări, acestea au PRIORITATE față de cerința inițială.
Răspunde în limba română."""


def node_clarify_task(state: AgentState) -> dict:
    """Cere LLM-ului să explice cum a înțeles task-ul."""
    understanding = ask_structured(TaskUnderstanding, SYSTEM_PROMPT, build_prompt(state))

    return {
        "clarification": format_understanding(understanding),
        "history": log_step("Am reformulat cerința și aștept confirmarea utilizatorului."),
    }


def build_prompt(state: AgentState) -> str:
    """Cerința + precizările utilizatorului + (dacă există) propunerea anterioară respinsă.

    Propunerea anterioară e necesară pentru că utilizatorul se referă adesea la ea
    ("schimbă a doua presupunere"), dar NU e prezentată ca înțelegere confirmată.
    """
    return join_sections(
        task_context(state, include_clarification=False),
        section("Propunerea ta anterioară (respinsă de utilizator)", state["clarification"])
        if state["clarification"]
        else None,
    )


def format_understanding(understanding: TaskUnderstanding) -> str:
    """Transformă obiectul structurat într-un text ușor de citit (pentru om ȘI pentru LLM)."""
    return join_sections(
        section("Rezumat", understanding.summary),
        section("Interfață propusă", bullet_list(understanding.interface)),
        section("Presupuneri", bullet_list(understanding.assumptions)),
        section("Întrebări deschise", bullet_list(understanding.open_questions))
        if understanding.open_questions
        else None,
    )
