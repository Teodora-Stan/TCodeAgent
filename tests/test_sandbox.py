"""Tests for utils/sandbox.py: runs real pytest on small code, in a temporary directory."""

from utils.sandbox import COLLECTION_ERROR, TIMEOUT_ERROR, run_tests

TESTS = """
from solution import add

def test_positive():
    assert add(1, 2) == 3

def test_negative():
    assert add(-1, -1) == -2
"""


def test_correct_code_passes():
    result = run_tests("def add(a, b):\n    return a + b\n", TESTS, timeout=30)
    assert result.passed
    assert result.total == 2
    assert result.failed_tests == []


def test_wrong_code_reports_failing_tests():
    result = run_tests("def add(a, b):\n    return a - b\n", TESTS, timeout=30)
    assert not result.passed
    assert sorted(result.failed_tests) == ["test_negative", "test_positive"]


def test_syntax_error_is_a_collection_error_not_a_test():
    result = run_tests("def add(:\n", TESTS, timeout=30)
    assert not result.passed
    assert result.failed_tests == [COLLECTION_ERROR]
    assert result.total == 0  # pytest's "fake" test is not counted


def test_infinite_loop_hits_timeout():
    result = run_tests("def add(a, b):\n    while True:\n        pass\n", TESTS, timeout=2)
    assert not result.passed
    assert result.failed_tests == [TIMEOUT_ERROR]
