"""Teste pentru logica din noduri care NU depinde de LLM."""

from nodes.execute_tests import update_streaks
from nodes.final_report import Outcome, detect_outcome
from nodes.implement_code import Mode, detect_mode


class TestUpdateStreaks:
    def test_consecutive_failures_are_counted(self):
        assert update_streaks({"test_a": 2}, ["test_a"]) == {"test_a": 3}

    def test_new_failure_starts_at_one(self):
        assert update_streaks({}, ["test_b"]) == {"test_b": 1}

    def test_tests_that_pass_again_are_removed(self):
        assert update_streaks({"test_a": 2, "test_b": 1}, ["test_b"]) == {"test_b": 2}


class TestDetectMode:
    def test_no_code_means_new(self, make_state):
        assert detect_mode(make_state(code="")) == Mode.NEW

    def test_failing_code_means_fix(self, make_state):
        assert detect_mode(make_state(code="x = 1", execution_passed=False)) == Mode.FIX

    def test_passing_code_means_refine(self, make_state):
        assert detect_mode(make_state(code="x = 1", execution_passed=True)) == Mode.REFINE


class TestDetectOutcome:
    def test_success(self, make_state):
        assert detect_outcome(make_state(execution_passed=True, code_judge_passed=True)) == Outcome.SUCCESS

    def test_passed_but_critic_unhappy(self, make_state):
        state = make_state(execution_passed=True, code_judge_passed=False)
        assert detect_outcome(state) == Outcome.PASSED_WITH_REMARKS

    def test_broken_after_refine_reverts(self, make_state):
        state = make_state(execution_passed=False, last_passing_code="x = 1")
        assert detect_outcome(state) == Outcome.REVERTED

    def test_never_passed_is_failure(self, make_state):
        assert detect_outcome(make_state(execution_passed=False)) == Outcome.FAILED
