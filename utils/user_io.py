"""
Interacțiunea cu utilizatorul (Human-in-the-Loop) prin `interrupt()` din LangGraph.

Cum funcționează `interrupt()`:
  1. Un nod apelează `interrupt(payload)` -> graful se OPREȘTE și salvează starea
     în checkpointer. `payload` ajunge la cel care rulează graful (main.py).
  2. main.py afișează întrebarea, citește răspunsul și reia graful cu
     `Command(resume=raspuns)`.
  3. Nodul este RE-EXECUTAT DE LA ÎNCEPUT, iar de data asta `interrupt()`
     întoarce direct răspunsul.

Consecință importantă: un nod care cere input NU trebuie să facă altceva
costisitor (ex: apeluri LLM) ÎNAINTE de `interrupt()`, pentru că s-ar repeta.
De aceea nodurile "user_*" doar întreabă și salvează răspunsul.
"""

from typing import TypedDict

from langgraph.types import interrupt


class UserPrompt(TypedDict):
    """Ce trimite graful către interfață când are nevoie de input."""

    title: str        # titlul scurt al pasului (ex: "Confirmare task")
    message: str      # contextul afișat (ex: cum a înțeles agentul task-ul)
    question: str     # întrebarea propriu-zisă
    multiline: bool   # True = utilizatorul poate lipi mai multe linii (ex: cod)


def ask_user(title: str, message: str, question: str, multiline: bool = False) -> str:
    """Oprește graful, așteaptă răspunsul utilizatorului și îl întoarce (ca text)."""
    prompt: UserPrompt = {
        "title": title,
        "message": message,
        "question": question,
        "multiline": multiline,
    }
    answer = interrupt(prompt)
    return str(answer or "").strip()
