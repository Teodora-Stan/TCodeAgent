"""
Tests for routers.py: the routing decisions for every branch of the graph.

The limits are read from SETTINGS (not hard-coded), so the tests stay
correct even if you change them in .env.
"""

import routers
from config import SETTINGS
from node_names import Node
from utils.sandbox import COLLECTION_ERROR


# ---------------------------------------------------------------- Phases 1-2


def test_confirm_routes(make_state):
    assert routers.route_after_confirm(make_state(user_confirmed_task=True)) == Node.GENERATE_TESTS
    assert routers.route_after_confirm(make_state(user_confirmed_task=False)) == Node.CLARIFY_TASK


def test_corner_cases_are_asked_only_once(make_state):
    assert routers.route_after_generate_tests(make_state(corner_cases_asked=False)) == Node.ASK_CORNER_CASES
    assert routers.route_after_generate_tests(make_state(corner_cases_asked=True)) == Node.JUDGE_TESTS


def test_user_corner_cases_trigger_regeneration(make_state):
    assert routers.route_after_corner_cases(make_state(user_corner_cases="input gol")) == Node.GENERATE_TESTS
    assert routers.route_after_corner_cases(make_state(user_corner_cases="")) == Node.JUDGE_TESTS


def test_test_judge_routes(make_state):
    limit = SETTINGS.max_test_judge_iterations
    approved = make_state(test_judge_passed=True)
    rejected = make_state(test_judge_passed=False, test_judge_iterations=limit - 1)
    exhausted = make_state(test_judge_passed=False, test_judge_iterations=limit)

    assert routers.route_after_test_judge(approved) == Node.IMPLEMENT_CODE
    assert routers.route_after_test_judge(rejected) == Node.GENERATE_TESTS
    assert routers.route_after_test_judge(exhausted) == Node.USER_MANUAL_TESTS


def test_manual_tests_with_error_ask_again(make_state):
    assert routers.route_after_manual_tests(make_state(manual_tests_error="linia 1")) == Node.USER_MANUAL_TESTS
    assert routers.route_after_manual_tests(make_state(manual_tests_error=None)) == Node.IMPLEMENT_CODE


# ---------------------------------------------------------------- Phase 3


def test_passing_execution_goes_to_code_judge(make_state):
    assert routers.route_after_execution(make_state(execution_passed=True)) == Node.JUDGE_CODE


def test_real_test_failure_is_diagnosed(make_state):
    state = make_state(failing_tests=["test_a"], failing_streaks={"test_a": 1}, failed_runs=1)
    assert routers.route_after_execution(state) == Node.DIAGNOSE_FAILURE


def test_collection_error_skips_diagnosis(make_state):
    state = make_state(failing_tests=[COLLECTION_ERROR], failing_streaks={COLLECTION_ERROR: 1}, failed_runs=1)
    assert routers.route_after_execution(state) == Node.IMPLEMENT_CODE


def test_no_diagnosis_after_max_test_repairs(make_state):
    state = make_state(failing_tests=["test_a"], failed_runs=1, test_repairs=SETTINGS.max_test_repairs)
    assert routers.route_after_execution(state) == Node.IMPLEMENT_CODE


def test_same_test_failing_too_often_stops_the_agent(make_state):
    state = make_state(
        failing_tests=["test_a"], failing_streaks={"test_a": SETTINGS.max_same_test_failures}, failed_runs=1
    )
    assert routers.route_after_execution(state) == Node.FINAL_REPORT


def test_too_many_failed_runs_stop_the_agent(make_state):
    state = make_state(failing_tests=["test_a"], failed_runs=SETTINGS.max_fix_attempts)
    assert routers.route_after_execution(state) == Node.FINAL_REPORT


def test_diagnosis_routes(make_state):
    assert routers.route_after_diagnosis(make_state(suspect_tests=["test_a: ..."])) == Node.CONFIRM_TEST_FIX
    assert routers.route_after_diagnosis(make_state(suspect_tests=[])) == Node.IMPLEMENT_CODE


def test_test_fix_confirm_routes(make_state):
    assert routers.route_after_test_fix_confirm(make_state(test_fix_approved=True)) == Node.REPAIR_TESTS
    assert routers.route_after_test_fix_confirm(make_state(test_fix_approved=False)) == Node.IMPLEMENT_CODE


def test_code_judge_routes(make_state):
    limit = SETTINGS.max_refine_iterations
    assert routers.route_after_code_judge(make_state(code_judge_passed=True)) == Node.FINAL_REPORT
    assert routers.route_after_code_judge(make_state(refine_iterations=limit)) == Node.IMPLEMENT_CODE
    assert routers.route_after_code_judge(make_state(refine_iterations=limit + 1)) == Node.FINAL_REPORT
