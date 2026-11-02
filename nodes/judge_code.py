"""
NODE: judge_code (Phase 3, LLM-as-a-judge)

Runs ONLY after all tests have passed. The critic checks what the tests can't:
readability, duplicated code, needless complexity, bugs on untested cases.
If it asks for changes, we go back to implement_code (in REFINE mode), at most
`max_refine_iterations` times.
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
    """Evaluates the quality of the code that passed the tests."""
    review = ask_structured(CodeReview, SYSTEM_PROMPT, build_prompt(state))

    update = {
        "code_judge_passed": review.approved,
        "code_judge_feedback": format_review(review),
    }
    if review.approved:
        update["history"] = log_step("Criticul de cod: APROBAT.")
    else:
        # The counter only grows on rejection = how many improvement rounds were requested.
        refine = state["refine_iterations"] + 1
        update["refine_iterations"] = refine
        update["history"] = log_step(
            f"Criticul de cod: cere îmbunătățiri (runda {refine}/{SETTINGS.max_refine_iterations}) - "
            f"{len(review.blocking_issues)} probleme."
        )
    return update


def build_prompt(state: AgentState) -> str:
    """The task context + the tests + the code to evaluate."""
    return join_sections(
        task_context(state),
        section(f"Testele ({TEST_FILE}) - toate trec", code_block(state["test_code"])),
        section(f"Codul de evaluat ({SOLUTION_FILE})", code_block(state["code"])),
    )


def format_review(review: CodeReview) -> str:
    """The critic's feedback as text (used in REFINE and in the final report)."""
    return join_sections(
        section("Probleme care trebuie rezolvate", bullet_list(review.blocking_issues)),
        section("Sugestii opționale", bullet_list(review.suggestions)),
    )
