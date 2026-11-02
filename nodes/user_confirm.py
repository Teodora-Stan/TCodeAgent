"""
NODE: user_confirm (Phase 1, Human-in-the-Loop)

Shows the user how the agent understood the task and waits for:
  - "ok" / "da" / Enter      -> confirmed, we move on to the tests
  - any other text           -> treated as a clarification; we go back to clarify_task

The node only asks and saves the answer (see the explanation in utils/user_io.py
about why we don't make LLM calls in a node with `interrupt()`).
"""

from state import AgentState
from utils.text import is_affirmative
from utils.user_io import ask_user


def node_user_confirm(state: AgentState) -> dict:
    """Asks for confirmation of how the task was understood."""
    answer = ask_user(
        title="Confirmare task",
        message=state["clarification"],
        question="Am înțeles corect? Scrie 'ok' pentru a continua sau descrie ce trebuie schimbat.",
    )

    if is_affirmative(answer):
        return {"user_confirmed_task": True}

    # The clarification is APPENDED to the history (operator.add reducer), not overwritten.
    return {"user_confirmed_task": False, "clarification_history": [answer]}
