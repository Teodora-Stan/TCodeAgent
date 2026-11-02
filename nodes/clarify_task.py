"""
NODE: clarify_task (Phase 1)

The agent rephrases the request, proposes the interface (the function signatures)
and states its assumptions. The result is shown to the user in the next node
(user_confirm). If the user disagrees, we come back here, and their feedback
appears in the prompt through `task_context` (the `clarification_history` field).
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
    """Asks the LLM to explain how it understood the task."""
    understanding = ask_structured(TaskUnderstanding, SYSTEM_PROMPT, build_prompt(state))

    return {
        "clarification": format_understanding(understanding),
        "history": log_step("Am reformulat cerința și aștept confirmarea utilizatorului."),
    }


def build_prompt(state: AgentState) -> str:
    """The request + the user's clarifications + (if any) the previous, rejected proposal.

    The previous proposal is needed because the user often refers to it
    ("change the second assumption"), but it is NOT presented as a confirmed understanding.
    """
    return join_sections(
        task_context(state, include_clarification=False),
        section("Propunerea ta anterioară (respinsă de utilizator)", state["clarification"])
        if state["clarification"]
        else None,
    )


def format_understanding(understanding: TaskUnderstanding) -> str:
    """Turns the structured object into easy-to-read text (for the human AND for the LLM)."""
    return join_sections(
        section("Rezumat", understanding.summary),
        section("Interfață propusă", bullet_list(understanding.interface)),
        section("Presupuneri", bullet_list(understanding.assumptions)),
        section("Întrebări deschise", bullet_list(understanding.open_questions))
        if understanding.open_questions
        else None,
    )
