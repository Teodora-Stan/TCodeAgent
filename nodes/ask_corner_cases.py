"""
NODE: ask_corner_cases (Phase 2, Human-in-the-Loop)

After the first test generation, we show the user which tests exist and ask
whether they have more corner case ideas. We ask ONLY ONCE (the
`corner_cases_asked` flag), not on every critic iteration.

  - empty answer  -> we go to the test critic
  - text answer   -> we go back to generate_tests so it adds them
"""

from state import AgentState
from utils.text import bullet_list, is_negative, list_test_names
from utils.user_io import ask_user


def node_ask_corner_cases(state: AgentState) -> dict:
    """Asks the user for additional corner cases."""
    answer = ask_user(
        title="Corner cases",
        message="Teste generate:\n" + bullet_list(list_test_names(state["test_code"])),
        question="Mai ai cazuri limită pe care vrei să le testăm? (Enter = nu)",
    )
    # "nu" / "nimic" / Enter -> "" (the router goes straight to the test critic).
    return {"corner_cases_asked": True, "user_corner_cases": "" if is_negative(answer) else answer}
