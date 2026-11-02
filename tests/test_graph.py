"""
Teste de integrare: întregul graf, cu LLM fals și răspunsuri de utilizator scriptate.

Verifică traseul complet prin noduri (inclusiv interrupt/resume), pytest-ul real
din sandbox și deciziile routerelor - totul fără niciun apel către Groq.
"""

import pytest
from langgraph.types import Command

import nodes.clarify_task
import nodes.diagnose_failure
import nodes.final_report
import nodes.generate_tests
import nodes.implement_code
import nodes.judge_code
import nodes.judge_tests
import nodes.repair_tests
from graph import build_graph
from nodes.final_report import Outcome
from schemas import CodeReview, FailureDiagnosis, TaskUnderstanding

# Alias-uri: altfel pytest ar încerca să colecteze clasele "Test*" ca teste.
from schemas import TestReview as Review
from schemas import TestVerdict as Verdict
from state import initial_state

# Suita generată de "LLM" conține un test GREȘIT: luna 90 nu e validă.
WRONG_TESTS = """
import pytest
from solution import valid_month

@pytest.mark.parametrize("month, expected", [(1, True), (12, True), (90, True)])
def test_month(month, expected):
    assert valid_month(month) is expected
"""
FIXED_TESTS = WRONG_TESTS.replace("(90, True)", "(90, False)")
CORRECT_CODE = "def valid_month(month: int) -> bool:\n    return 1 <= month <= 12\n"
BROKEN_CODE = "def valid_month(month: int) -> bool:\n    return False\n"


def run_graph(answers: dict[str, str]) -> dict:
    """Rulează graful cap-coadă; `answers` = {titlul întrebării: răspuns}."""
    app = build_graph()  # checkpointer în memorie
    config = {"configurable": {"thread_id": "test"}, "recursion_limit": 100}
    graph_input = initial_state("validează luna")

    while True:
        prompt = None
        for update in app.stream(graph_input, config, stream_mode="updates"):
            if "__interrupt__" in update:
                prompt = update["__interrupt__"][0].value
        if prompt is None:
            return app.get_state(config).values
        graph_input = Command(resume=answers[prompt["title"]])


@pytest.fixture
def fake_llm(monkeypatch):
    """LLM fals: fiecare nod primește un răspuns fix; codul generat e configurabil."""
    generated_code = {"value": CORRECT_CODE}

    def patch(module, name, response):
        monkeypatch.setattr(module, name, lambda *args, **kwargs: response)

    patch(nodes.clarify_task, "ask_structured", TaskUnderstanding(summary="s", interface=[], assumptions=[]))
    patch(nodes.generate_tests, "ask_code", WRONG_TESTS)
    patch(nodes.judge_tests, "ask_structured", Review(approved=True, score=8))
    patch(nodes.repair_tests, "ask_code", FIXED_TESTS)
    patch(nodes.judge_code, "ask_structured", CodeReview(approved=True))
    patch(nodes.final_report, "ask_text", "raport")
    patch(
        nodes.diagnose_failure,
        "ask_structured",
        FailureDiagnosis(verdicts=[Verdict(test_name="test_month[90-True]", culprit="test", reason="luna 90")]),
    )
    monkeypatch.setattr(nodes.implement_code, "ask_code", lambda *args: generated_code["value"])
    return generated_code


def test_wrong_test_is_repaired_when_user_agrees(fake_llm):
    final = run_graph({"Confirmare task": "ok", "Corner cases": "", "Test posibil greșit": "da"})

    assert final["execution_passed"]
    assert final["test_repairs"] == 1
    assert final["code_iterations"] == 1  # codul corect NU a fost modificat
    assert "(90, False)" in final["test_code"]
    assert Outcome.SUCCESS in final["final_report"]


def test_user_rejecting_the_test_fix_keeps_the_tests(fake_llm):
    final = run_graph({"Confirmare task": "ok", "Corner cases": "", "Test posibil greșit": "nu"})

    assert final["test_repairs"] == 0
    assert "(90, True)" in final["test_code"]
    assert not final["execution_passed"]  # codul corect nu poate trece un test greșit


def test_agent_stops_when_code_cannot_be_fixed(fake_llm):
    fake_llm["value"] = BROKEN_CODE
    final = run_graph({"Confirmare task": "ok", "Corner cases": "", "Test posibil greșit": "nu"})

    assert not final["execution_passed"]
    assert Outcome.FAILED in final["final_report"]
