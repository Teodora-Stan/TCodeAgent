"""
NODE: user_manual_tests (Phase 2, Human-in-the-Loop, fallback)

We get here when the test critic rejected the suite too many times. We show the
user what the critic was missing and let them paste hand-written tests
(which are APPENDED to the existing suite).

  - empty answer        -> continue with the current suite
  - valid code          -> append it and continue
  - code with an error  -> set `manual_tests_error`; the router sends us back here
"""

from state import AgentState
from utils.text import join_sections, section, syntax_error
from utils.user_io import ask_user


def node_user_manual_tests(state: AgentState) -> dict:
    """Lets the user extend the test suite manually."""
    answer = ask_user(
        title="Criticul de teste nu e încă mulțumit",
        message=build_message(state),
        question=(
            "Lipește teste pytest suplimentare (se adaugă la suită), "
            "sau lasă gol pentru a continua cu suita actuală."
        ),
        multiline=True,
    )

    if not answer:
        return {"manual_tests_error": None}

    # We check the syntax of the COMBINED suite: that way we also catch wrong indentation.
    combined = f"{state['test_code'].rstrip()}\n\n\n# --- Teste adăugate manual ---\n{answer}\n"
    error = syntax_error(combined)
    if error:
        return {"manual_tests_error": f"Testele adăugate au o eroare de sintaxă ({error})."}

    return {
        "test_code": combined,
        "manual_tests_error": None,
        "history": ["Utilizatorul a adăugat teste manual."],
    }


def build_message(state: AgentState) -> str:
    """What the user sees: any previous error + the critic's feedback."""
    return join_sections(
        section("Eroare", state["manual_tests_error"]) if state["manual_tests_error"] else None,
        state["test_judge_feedback"],
    )
