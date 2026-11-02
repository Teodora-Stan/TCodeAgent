"""
Pieces reused by several nodes (the task context and logging).
"""

from state import AgentState
from utils.text import bullet_list, join_sections, section


def task_context(state: AgentState, include_clarification: bool = True) -> str:
    """The context shared by almost all prompts: the request + what was understood.

    We build it in a single function so that all nodes see EXACTLY the same
    information about the task (otherwise the tests and the code might "understand" it differently).

    `include_clarification=False` is used by clarify_task, which doesn't have a
    confirmed understanding of the task yet.
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
    """Prints progress to the console and returns the entry for the `history` field.

    Usage in a node:  `return {..., "history": log_step("Am generat testele")}`
    (the `operator.add` reducer in AgentState appends it to the log).
    """
    print(f"  ▸ {message}")
    return [message]
