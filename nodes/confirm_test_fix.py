"""
NOD: confirm_test_fix (Faza 3b, Human-in-the-Loop)

LLM-ul crede că unele teste sunt greșite. Nu le modificăm fără acordul
utilizatorului (altfel agentul ar putea "trișa" schimbând testele ca să treacă).

  - "da" / Enter      -> corectăm testele (repair_tests)
  - "nu"              -> testele sunt corecte, reparăm codul (implement_code)
  - alt text          -> corectăm testele, folosind textul ca indicații
"""

from state import AgentState
from utils.text import bullet_list, is_affirmative, is_negative
from utils.user_io import ask_user

# Adăugat la diagnostic când utilizatorul respinge corectarea, ca implement_code
# să știe că testele sunt corecte și să nu mai "lupte" cu ele.
TESTS_CONFIRMED_NOTE = "\n\nUtilizatorul a confirmat că testele sunt CORECTE: repară codul."


def node_confirm_test_fix(state: AgentState) -> dict:
    """Întreabă utilizatorul dacă testele suspectate trebuie corectate."""
    answer = ask_user(
        title="Test posibil greșit",
        message="Cred că aceste teste au valori așteptate greșite:\n" + bullet_list(state["suspect_tests"]),
        question=(
            "Corectez testele? 'da' (Enter) = corectez testele, 'nu' = testele sunt bune, repară codul, "
            "sau scrie ce anume trebuie corectat."
        ),
    )

    # Ordinea contează: Enter gol e în ambele mulțimi, iar aici îl vrem ca "da".
    if is_affirmative(answer):
        return {"test_fix_approved": True, "test_fix_guidance": ""}

    if is_negative(answer):
        return {
            "test_fix_approved": False,
            "failure_diagnosis": state["failure_diagnosis"] + TESTS_CONFIRMED_NOTE,
            "history": ["Utilizatorul a confirmat că testele sunt corecte."],
        }

    # Text liber (ex: "luna 90 e invalidă, deci False") -> indicație pentru reparare.
    return {"test_fix_approved": True, "test_fix_guidance": answer}
