"""
Funcții mici de lucru cu text, refolosite de mai multe noduri.

Ideea: prompt-urile sunt construite din "secțiuni" (titlu + conținut), ca să nu
repetăm în fiecare nod același cod de formatare.
"""

import ast
import re

# Răspunsuri considerate "da, e ok" când utilizatorul confirmă ceva.
AFFIRMATIVE_ANSWERS = {"", "ok", "da", "yes", "y", "d", "bine", "corect", "confirm"}

# Răspunsuri considerate "nu am nimic de adăugat" (ex: la întrebarea de corner cases).
NEGATIVE_ANSWERS = {"", "nu", "no", "n", "nimic", "-", "gata", "skip"}


def strip_reasoning(text: str) -> str:
    """Șterge blocurile `<think>...</think>` pe care unele modele (ex: Qwen3) le pun în răspuns."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def extract_code_block(text: str) -> str:
    """Scoate codul din primul bloc ```python ... ``` (sau ``` ... ```).

    Dacă modelul n-a folosit blocuri de cod, presupunem că tot textul e cod.
    """
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.DOTALL)
    return (match.group(1) if match else text).strip() + "\n"


def code_block(code: str, language: str = "python") -> str:
    """Pune codul într-un bloc markdown, ca LLM-ul să-l distingă de instrucțiuni."""
    return f"```{language}\n{code.strip()}\n```"


def bullet_list(items: list[str], empty: str = "(nimic)") -> str:
    """Transformă o listă în bullet points; `empty` dacă lista e goală."""
    return "\n".join(f"- {item}" for item in items) if items else empty


def section(title: str, body: str) -> str:
    """O secțiune de prompt: `## Titlu` urmat de conținut."""
    return f"## {title}\n{body.strip()}"


def join_sections(*sections: str | None) -> str:
    """Lipește secțiunile, ignorând-o pe cele goale (`None` sau "")."""
    return "\n\n".join(s for s in sections if s)


def truncate(text: str, max_chars: int = 4000) -> str:
    """Taie textele lungi (ex: output pytest) păstrând FINALUL, unde sunt erorile."""
    if len(text) <= max_chars:
        return text
    return "...(trunchiat)...\n" + text[-max_chars:]


def is_affirmative(answer: str) -> bool:
    """True dacă răspunsul utilizatorului înseamnă confirmare ("ok", "da", Enter gol...)."""
    return answer.strip().lower() in AFFIRMATIVE_ANSWERS


def list_test_names(test_code: str) -> list[str]:
    """Numele funcțiilor `test_*` dintr-un fișier de teste (fără să-l ruleze)."""
    try:
        tree = ast.parse(test_code)
    except SyntaxError:
        return []
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]


def is_negative(answer: str) -> bool:
    """True dacă utilizatorul a spus că nu are nimic de adăugat ("nu", Enter gol...)."""
    return answer.strip().lower() in NEGATIVE_ANSWERS


def syntax_error(code: str) -> str | None:
    """Verifică sintaxa Python fără să ruleze codul. `None` = cod valid."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as exc:
        return f"linia {exc.lineno}: {exc.msg}"
