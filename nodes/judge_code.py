"""
NOD: judge_code (Faza 3, LLM-as-a-judge)

Rulează DOAR după ce toate testele au trecut. Criticul verifică ce testele nu
pot verifica: lizibilitate, cod duplicat, complexitate inutilă, bug-uri pe
cazuri netestate. Dacă cere modificări, ne întoarcem la implement_code (în
modul REFINE), de cel mult `max_refine_iterations` ori.
"""

from config import SETTINGS
from llm import ask_structured
from nodes.common import log_step, task_context
from schemas import CodeReview
from state import AgentState
from utils.sandbox import SOLUTION_FILE, TEST_FILE
from utils.text import bullet_list, code_block, join_sections, section

SYSTEM_PROMPT = """\
Ești un reviewer de cod Python pragmatic. Codul a trecut deja toate testele.
Evaluează: corectitudine pe cazuri netestate, claritate, modularitate, duplicare, complexitate.
Setează approved=false DOAR pentru probleme care chiar merită o nouă iterație
(bug-uri, cod greu de înțeles, duplicare evidentă). Detaliile minore merg la `suggestions`.
Răspunde în limba română."""


def node_judge_code(state: AgentState) -> dict:
    """Evaluează calitatea codului care a trecut testele."""
    review = ask_structured(CodeReview, SYSTEM_PROMPT, build_prompt(state))

    update = {
        "code_judge_passed": review.approved,
        "code_judge_feedback": format_review(review),
    }
    if review.approved:
        update["history"] = log_step("Criticul de cod: APROBAT.")
    else:
        # Contorul crește doar la respingere = câte runde de îmbunătățire s-au cerut.
        refine = state["refine_iterations"] + 1
        update["refine_iterations"] = refine
        update["history"] = log_step(
            f"Criticul de cod: cere îmbunătățiri (runda {refine}/{SETTINGS.max_refine_iterations}) - "
            f"{len(review.blocking_issues)} probleme."
        )
    return update


def build_prompt(state: AgentState) -> str:
    """Contextul task-ului + testele + codul de evaluat."""
    return join_sections(
        task_context(state),
        section(f"Testele ({TEST_FILE}) - toate trec", code_block(state["test_code"])),
        section(f"Codul de evaluat ({SOLUTION_FILE})", code_block(state["code"])),
    )


def format_review(review: CodeReview) -> str:
    """Feedback-ul criticului ca text (folosit în REFINE și în raportul final)."""
    return join_sections(
        section("Probleme care trebuie rezolvate", bullet_list(review.blocking_issues)),
        section("Sugestii opționale", bullet_list(review.suggestions)),
    )
