"""
NOD: user_manual_tests (Faza 2, Human-in-the-Loop, fallback)

Ajungem aici când criticul de teste a respins suita de prea multe ori. Îi arătăm
utilizatorului ce i-a lipsit criticului și îl lăsăm să lipească teste scrise de
mână (care se ADAUGĂ la suita existentă).

  - răspuns gol         -> continuăm cu suita actuală
  - cod valid           -> îl adăugăm și continuăm
  - cod cu eroare       -> setăm `manual_tests_error`; router-ul ne trimite înapoi aici
"""

from state import AgentState
from utils.text import join_sections, section, syntax_error
from utils.user_io import ask_user


def node_user_manual_tests(state: AgentState) -> dict:
    """Permite utilizatorului să completeze manual suita de teste."""
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

    # Verificăm sintaxa pe suita COMBINATĂ: așa prindem și indentarea greșită.
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
    """Ce vede utilizatorul: eventuala eroare anterioară + feedback-ul criticului."""
    return join_sections(
        section("Eroare", state["manual_tests_error"]) if state["manual_tests_error"] else None,
        state["test_judge_feedback"],
    )
