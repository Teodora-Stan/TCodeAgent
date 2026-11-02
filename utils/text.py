"""
Small text helpers, reused by several nodes.

The idea: prompts are built from "sections" (title + content), so we don't
repeat the same formatting code in every node.
"""

import ast
import re

# Answers that count as "yes, that's ok" when the user confirms something.
AFFIRMATIVE_ANSWERS = {"", "ok", "da", "yes", "y", "d", "bine", "corect", "confirm"}

# Answers that count as "I have nothing to add" (e.g. to the corner cases question).
NEGATIVE_ANSWERS = {"", "nu", "no", "n", "nimic", "-", "gata", "skip"}


def strip_reasoning(text: str) -> str:
    """Removes the `<think>...</think>` blocks some models (e.g. Qwen3) put in their answer."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def extract_code_block(text: str) -> str:
    """Extracts the code from the first ```python ... ``` (or ``` ... ```) block.

    If the model didn't use code blocks, we assume the whole text is code.
    """
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.DOTALL)
    return (match.group(1) if match else text).strip() + "\n"


def code_block(code: str, language: str = "python") -> str:
    """Wraps code in a markdown block, so the LLM can tell it apart from instructions."""
    return f"```{language}\n{code.strip()}\n```"


def bullet_list(items: list[str], empty: str = "(nimic)") -> str:
    """Turns a list into bullet points; `empty` if the list is empty."""
    return "\n".join(f"- {item}" for item in items) if items else empty


def section(title: str, body: str) -> str:
    """A prompt section: `## Title` followed by the content."""
    return f"## {title}\n{body.strip()}"


def join_sections(*sections: str | None) -> str:
    """Joins the sections, skipping the empty ones (`None` or "")."""
    return "\n\n".join(s for s in sections if s)


def truncate(text: str, max_chars: int = 4000) -> str:
    """Cuts long texts (e.g. pytest output) keeping the END, where the errors are."""
    if len(text) <= max_chars:
        return text
    return "...(trunchiat)...\n" + text[-max_chars:]


def is_affirmative(answer: str) -> bool:
    """True if the user's answer means confirmation ("ok", "da", empty Enter...)."""
    return answer.strip().lower() in AFFIRMATIVE_ANSWERS


def list_test_names(test_code: str) -> list[str]:
    """The names of the `test_*` functions in a test file (without running it)."""
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
    """True if the user said they have nothing to add ("nu", empty Enter...)."""
    return answer.strip().lower() in NEGATIVE_ANSWERS


def syntax_error(code: str) -> str | None:
    """Checks Python syntax without running the code. `None` = valid code."""
    try:
        ast.parse(code)
        return None
    except SyntaxError as exc:
        return f"linia {exc.lineno}: {exc.msg}"
