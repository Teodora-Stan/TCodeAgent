"""
NOD: final_report (Faza 4)

1. Stabilește rezultatul final (succes / succes cu observații / revenire la
   ultima versiune verde / eșec).
2. Cere LLM-ului un raport: ce s-a implementat, explicația codului, impresii critice.
3. Salvează codul, testele și raportul în `SETTINGS.output_dir`.

Partea "factuală" a raportului (statusul, numărul de iterații) e generată din
cod, nu de LLM, ca să nu poată fi "inventată".
"""

from enum import StrEnum
from pathlib import Path

from config import SETTINGS
from llm import ask_text
from nodes.common import log_step, task_context
from state import AgentState
from utils.sandbox import SOLUTION_FILE, TEST_FILE
from utils.text import bullet_list, code_block, join_sections, section

REPORT_FILE = "REPORT.md"

SYSTEM_PROMPT = """\
Ești un inginer senior care predă munca unui coleg. Scrie un raport în markdown, în română, cu secțiunile:
## Ce s-a implementat   - pe scurt, ce face modulul
## Explicația codului   - fiecare funcție/clasă: rol, parametri, ce întoarce, decizii importante
## Teste                - ce acoperă suita și ce NU acoperă
## Impresii critice     - limitări, riscuri, ce ai îmbunătăți în continuare (fii onest)
Fii concret și concis. Dacă rezultatul NU e un succes, explică de ce agentul nu a reușit."""


class Outcome(StrEnum):
    """Rezultatul final al rulării."""

    SUCCESS = "✅ Succes: testele trec și criticul a aprobat codul"
    PASSED_WITH_REMARKS = "🟡 Testele trec, dar criticul de cod mai are observații"
    REVERTED = "🟡 Ultima îmbunătățire a stricat testele; s-a revenit la ultima versiune care trecea"
    FAILED = "❌ Eșec: agentul nu a reușit să treacă toate testele"


def node_final_report(state: AgentState) -> dict:
    """Generează raportul final și salvează rezultatele pe disc."""
    outcome = detect_outcome(state)
    # La REVERTED livrăm ultima versiune verde, nu cea stricată.
    final_code = state["last_passing_code"] if outcome == Outcome.REVERTED else state["code"]

    llm_report = ask_text(SYSTEM_PROMPT, build_prompt(state, outcome, final_code))
    report = join_sections(f"# Raport final\n\n**Status:** {outcome}", stats_section(state), llm_report)

    output_dir = save_outputs(SETTINGS.output_dir, final_code, state["test_code"], report)

    return {
        "code": final_code,
        "final_report": report,
        "history": log_step(f"Raport salvat în {output_dir / REPORT_FILE}."),
    }


def detect_outcome(state: AgentState) -> Outcome:
    """Deduce rezultatul din stare (aceeași logică pe care au folosit-o routerele)."""
    if state["execution_passed"]:
        return Outcome.SUCCESS if state["code_judge_passed"] else Outcome.PASSED_WITH_REMARKS
    if state["last_passing_code"]:
        return Outcome.REVERTED
    return Outcome.FAILED


def stats_section(state: AgentState) -> str:
    """Statistici deterministe despre rulare (fără LLM)."""
    stats = [
        f"Generări ale suitei de teste: {state['test_generations']}",
        f"Runde ale criticului de teste: {state['test_judge_iterations']}",
        f"Versiuni de cod generate: {state['code_iterations']}",
        f"Rulări cu teste picate: {state['failed_runs']}",
        f"Corectări ale testelor greșite: {state['test_repairs']}",
        f"Runde de îmbunătățire cerute de criticul de cod: {state['refine_iterations']}",
    ]
    if state["failing_tests"]:
        stats.append("Teste care încă pică: " + ", ".join(state["failing_tests"]))
    return section("Statistici", bullet_list(stats))


def build_prompt(state: AgentState, outcome: Outcome, final_code: str) -> str:
    """Tot ce trebuie să știe LLM-ul ca să scrie raportul."""
    return join_sections(
        task_context(state),
        section("Rezultat", str(outcome)),
        section(f"Codul final ({SOLUTION_FILE})", code_block(final_code)),
        section(f"Testele ({TEST_FILE})", code_block(state["test_code"])),
        section("Ultimul output pytest", code_block(state["execution_output"], language="text"))
        if not state["execution_passed"]
        else None,
        section("Observațiile criticului de cod", state["code_judge_feedback"])
        if state["code_judge_feedback"]
        else None,
        section("Jurnalul agentului", bullet_list(state["history"])),
    )


def save_outputs(output_dir: Path, code: str, test_code: str, report: str) -> Path:
    """Scrie solution.py, test_solution.py și REPORT.md în directorul de output."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / SOLUTION_FILE).write_text(code, encoding="utf-8")
    (output_dir / TEST_FILE).write_text(test_code, encoding="utf-8")
    (output_dir / REPORT_FILE).write_text(report, encoding="utf-8")
    return output_dir
