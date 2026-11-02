"""
Bucăți refolosite de mai multe noduri (contextul task-ului și jurnalizarea).
"""

from state import AgentState
from utils.text import bullet_list, join_sections, section


def task_context(state: AgentState, include_clarification: bool = True) -> str:
    """Contextul comun pentru aproape toate prompt-urile: cerința + ce s-a înțeles.

    Îl construim într-o singură funcție ca toate nodurile să vadă EXACT aceleași
    informații despre task (altfel testele și codul ar putea "înțelege" diferit).

    `include_clarification=False` e folosit de clarify_task, care încă nu are o
    înțelegere confirmată a task-ului.
    """
    feedback = state["clarification_history"]
    return join_sections(
        section("Cerința utilizatorului", state["task"]),
        section("Precizări ulterioare ale utilizatorului", bullet_list(feedback)) if feedback else None,
        section("Înțelegerea confirmată a task-ului", state["clarification"])
        if include_clarification and state["clarification"]
        else None,
    )


def log_step(message: str) -> list[str]:
    """Afișează progresul în consolă și întoarce intrarea pentru câmpul `history`.

    Utilizare într-un nod:  `return {..., "history": log_step("Am generat testele")}`
    (reducer-ul `operator.add` din AgentState o adaugă la jurnal).
    """
    print(f"  ▸ {message}")
    return [message]
