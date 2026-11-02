"""
Interaction with the user (Human-in-the-Loop) through LangGraph's `interrupt()`.

How `interrupt()` works:
  1. A node calls `interrupt(payload)` -> the graph STOPS and saves the state
     in the checkpointer. `payload` reaches whoever runs the graph (main.py).
  2. main.py shows the question, reads the answer and resumes the graph with
     `Command(resume=answer)`.
  3. The node is RE-EXECUTED FROM THE START, and this time `interrupt()`
     returns the answer directly.

Important consequence: a node that asks for input must NOT do anything else
expensive (e.g. LLM calls) BEFORE `interrupt()`, because it would be repeated.
That's why the "user_*" nodes only ask and save the answer.
"""

from typing import TypedDict

from langgraph.types import interrupt


class UserPrompt(TypedDict):
    """What the graph sends to the interface when it needs input."""

    title: str        # short title of the step (e.g. "Confirmare task")
    message: str      # the context shown (e.g. how the agent understood the task)
    question: str     # the actual question
    multiline: bool   # True = the user can paste several lines (e.g. code)


def ask_user(title: str, message: str, question: str, multiline: bool = False) -> str:
    """Stops the graph, waits for the user's answer and returns it (as text)."""
    prompt: UserPrompt = {
        "title": title,
        "message": message,
        "question": question,
        "multiline": multiline,
    }
    answer = interrupt(prompt)
    return str(answer or "").strip()
