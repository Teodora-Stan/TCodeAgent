"""
NOD: user_confirm (Faza 1, Human-in-the-Loop)

Arată utilizatorului cum a înțeles agentul task-ul și așteaptă:
  - "ok" / "da" / Enter      -> confirmat, trecem la teste
  - orice alt text           -> e tratat ca precizare; ne întoarcem la clarify_task

Nodul doar întreabă și salvează răspunsul (vezi explicația din utils/user_io.py
despre de ce nu facem apeluri LLM într-un nod cu `interrupt()`).
"""

from state import AgentState
from utils.text import is_affirmative
from utils.user_io import ask_user


def node_user_confirm(state: AgentState) -> dict:
    """Cere confirmarea înțelegerii task-ului."""
    answer = ask_user(
        title="Confirmare task",
        message=state["clarification"],
        question="Am înțeles corect? Scrie 'ok' pentru a continua sau descrie ce trebuie schimbat.",
    )

    if is_affirmative(answer):
        return {"user_confirmed_task": True}

    # Precizarea se ADAUGĂ la istoric (reducer operator.add), nu suprascrie.
    return {"user_confirmed_task": False, "clarification_history": [answer]}
