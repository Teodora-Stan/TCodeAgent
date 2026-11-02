"""
NOD: diagnose_failure (Faza 3b, LLM-as-a-judge)

Testele sunt și ele generate de un LLM, deci pot fi GREȘITE (ex: un CNP cu luna
90 marcat ca valid). Fără acest nod, agentul ar "repara" codul ca să satisfacă
un test greșit și ar strica un cod corect.

Pentru fiecare test picat, LLM-ul decide cine e de vină:
  - "code" -> explicația ajunge în prompt-ul lui implement_code (ajută la reparare)
  - "test" -> testul ajunge în `suspect_tests`; utilizatorul decide în confirm_test_fix
"""

from llm import ask_structured
from nodes.common import log_step, task_context
from schemas import FailureDiagnosis, TestVerdict
from state import AgentState
from utils.sandbox import SOLUTION_FILE, TEST_FILE
from utils.text import bullet_list, code_block, join_sections, section

SYSTEM_PROMPT = """\
Ești un arbitru imparțial. Unele teste pytest au picat și trebuie să decizi, pentru FIECARE test picat,
dacă de vină e implementarea ("code") sau testul ("test").
Metodă:
1. Pornește DOAR de la cerință, nu de la cod și nici de la test.
2. Calculează independent, pas cu pas, rezultatul corect pentru input-ul testului.
3. Compară cu valoarea așteptată de test și cu ce a returnat codul.
Alege "test" doar dacă valoarea așteptată de test contrazice clar cerința; în caz de dubiu alege "code".
Răspunde în limba română."""


def node_diagnose_failure(state: AgentState) -> dict:
    """Stabilește, pentru fiecare test picat, dacă e de vină codul sau testul."""
    diagnosis = ask_structured(FailureDiagnosis, SYSTEM_PROMPT, build_prompt(state))
    suspects = [v for v in diagnosis.verdicts if v.culprit == "test"]

    return {
        "failure_diagnosis": format_diagnosis(diagnosis.verdicts),
        "suspect_tests": [format_verdict(v) for v in suspects],
        "history": log_step(
            f"Diagnostic: {len(diagnosis.verdicts) - len(suspects)} eșecuri din cauza codului, "
            f"{len(suspects)} teste suspectate ca greșite."
        ),
    }


def build_prompt(state: AgentState) -> str:
    """Cerința + codul + testele + ce a picat (cu output-ul pytest)."""
    return join_sections(
        task_context(state),
        section(f"Codul ({SOLUTION_FILE})", code_block(state["code"])),
        section(f"Testele ({TEST_FILE})", code_block(state["test_code"])),
        section("Teste picate", bullet_list(state["failing_tests"])),
        section("Output pytest", code_block(state["execution_output"], language="text")),
    )


def format_verdict(verdict: TestVerdict) -> str:
    """Un verdict pe un singur rând (+ corecția propusă, dacă există)."""
    line = f"{verdict.test_name}: {verdict.reason}"
    if verdict.corrected_expectation:
        line += f" → corect ar fi: {verdict.corrected_expectation}"
    return line


def format_diagnosis(verdicts: list[TestVerdict]) -> str:
    """Toate verdictele, grupate după vinovat (pentru prompt-ul de reparare a codului)."""
    code_bugs = [format_verdict(v) for v in verdicts if v.culprit == "code"]
    test_bugs = [format_verdict(v) for v in verdicts if v.culprit == "test"]
    return join_sections(
        section("Eșecuri cauzate de cod", bullet_list(code_bugs)) if code_bugs else None,
        section("Teste suspectate ca greșite", bullet_list(test_bugs)) if test_bugs else None,
    )
