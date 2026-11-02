"""
NOD: judge_tests (Faza 2, LLM-as-a-judge)

Un "critic" evaluează suita de teste ÎNAINTE de implementare: acoperă cerința?
Lipsesc cazuri limită? Sunt valori așteptate greșite?

Dacă respinge, feedback-ul lui ajunge în prompt-ul lui generate_tests. După
`max_test_judge_iterations` respingeri, utilizatorul e rugat să intervină manual.
"""

from config import SETTINGS
from llm import ask_structured
from nodes.common import log_step, task_context
from schemas import TestReview
from state import AgentState
from utils.text import bullet_list, code_block, join_sections, section

SYSTEM_PROMPT = """\
Ești un reviewer strict de teste pytest. Implementarea NU există încă; judeci doar testele.
Verifică:
1. Acoperirea cerinței și a interfeței confirmate.
2. Cazurile limită (input gol, valori extreme, erori așteptate).
3. CORECTITUDINEA valorilor așteptate - recalculează-le mental pentru fiecare aserțiune.
4. Calitatea: aserțiuni precise, teste independente și deterministe.
Aprobă (approved=true) dacă suita e suficient de bună pentru a ghida implementarea;
nu respinge pentru detalii minore de stil. Răspunde în limba română."""


def node_judge_tests(state: AgentState) -> dict:
    """Evaluează suita de teste și decide dacă e aprobată."""
    review = ask_structured(TestReview, SYSTEM_PROMPT, build_prompt(state))
    iteration = state["test_judge_iterations"] + 1
    verdict = "APROBAT" if review.approved else "RESPINS"

    return {
        "test_judge_passed": review.approved,
        "test_judge_feedback": "" if review.approved else format_review(review),
        "test_judge_iterations": iteration,
        "history": log_step(
            f"Criticul de teste (runda {iteration}/{SETTINGS.max_test_judge_iterations}): "
            f"{verdict}, scor {review.score}/10."
        ),
    }


def build_prompt(state: AgentState) -> str:
    """Contextul task-ului + suita de evaluat."""
    return join_sections(
        task_context(state),
        section("Suita de teste de evaluat", code_block(state["test_code"])),
    )


def format_review(review: TestReview) -> str:
    """Feedback-ul criticului ca text (citit atât de LLM, cât și de utilizator)."""
    return join_sections(
        section("Cazuri lipsă", bullet_list(review.missing_cases)),
        section("Probleme în testele existente", bullet_list(review.problems)),
    )
