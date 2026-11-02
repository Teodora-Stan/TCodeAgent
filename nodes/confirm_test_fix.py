"""
NODE: confirm_test_fix (Phase 3b, Human-in-the-Loop)

The LLM believes some tests are wrong. We don't change them without the user's
consent (otherwise the agent could "cheat" by changing the tests so they pass).

  - "da" / Enter      -> correct the tests (repair_tests)
  - "nu"              -> the tests are correct, fix the code (implement_code)
  - other text        -> correct the tests, using the text as guidance
"""

from state import AgentState
from utils.text import bullet_list, is_affirmative, is_negative
from utils.user_io import ask_user

# Appended to the diagnosis when the user rejects the correction, so implement_code
# knows the tests are correct and stops "fighting" them.
TESTS_CONFIRMED_NOTE = "\n\nUtilizatorul a confirmat că testele sunt CORECTE: repară codul."


def node_confirm_test_fix(state: AgentState) -> dict:
    """Asks the user whether the suspected tests should be corrected."""
    answer = ask_user(
        title="Test posibil greșit",
        message="Cred că aceste teste au valori așteptate greșite:\n" + bullet_list(state["suspect_tests"]),
        question=(
            "Corectez testele? 'da' (Enter) = corectez testele, 'nu' = testele sunt bune, repară codul, "
            "sau scrie ce anume trebuie corectat."
        ),
    )

    # Order matters: an empty Enter is in both sets, and here we want it to mean "da".
    if is_affirmative(answer):
        return {"test_fix_approved": True, "test_fix_guidance": ""}

    if is_negative(answer):
        return {
            "test_fix_approved": False,
            "failure_diagnosis": state["failure_diagnosis"] + TESTS_CONFIRMED_NOTE,
            "history": ["Utilizatorul a confirmat că testele sunt corecte."],
        }

    # Free text (e.g. "luna 90 e invalidă, deci False") -> guidance for the correction.
    return {"test_fix_approved": True, "test_fix_guidance": answer}
