"""
NOD: ask_corner_cases (Faza 2, Human-in-the-Loop)

După prima generare a testelor, îi arătăm utilizatorului ce teste există și îl
întrebăm dacă mai are idei de cazuri limită. Se întreabă O SINGURĂ DATĂ
(flag-ul `corner_cases_asked`), nu la fiecare iterație a criticului.

  - răspuns gol   -> mergem la criticul de teste
  - răspuns text  -> ne întoarcem la generate_tests ca să le adauge
"""

from state import AgentState
from utils.text import bullet_list, is_negative, list_test_names
from utils.user_io import ask_user


def node_ask_corner_cases(state: AgentState) -> dict:
    """Cere utilizatorului corner cases suplimentare."""
    answer = ask_user(
        title="Corner cases",
        message="Teste generate:\n" + bullet_list(list_test_names(state["test_code"])),
        question="Mai ai cazuri limită pe care vrei să le testăm? (Enter = nu)",
    )
    # "nu" / "nimic" / Enter -> "" (router-ul trece direct la criticul de teste).
    return {"corner_cases_asked": True, "user_corner_cases": "" if is_negative(answer) else answer}
