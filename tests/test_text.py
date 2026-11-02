"""Teste pentru utils/text.py (funcții pure, fără LLM)."""

import pytest

from utils.text import (
    extract_code_block,
    is_affirmative,
    is_negative,
    list_test_names,
    strip_reasoning,
    syntax_error,
    truncate,
)


class TestExtractCodeBlock:
    def test_extracts_python_block_from_prose(self):
        reply = "Iată codul:\n```python\nx = 1\n```\nSper că ajută."
        assert extract_code_block(reply) == "x = 1\n"

    def test_accepts_block_without_language(self):
        assert extract_code_block("```\ny = 2\n```") == "y = 2\n"

    def test_takes_only_the_first_block(self):
        assert extract_code_block("```python\na = 1\n```\n```python\nb = 2\n```") == "a = 1\n"

    def test_without_block_returns_whole_text(self):
        assert extract_code_block("z = 3") == "z = 3\n"


def test_strip_reasoning_removes_think_blocks():
    assert strip_reasoning("<think>\nhmm...\n</think>\nRăspuns") == "Răspuns"


@pytest.mark.parametrize("answer", ["", "ok", "OK", " da ", "yes"])
def test_is_affirmative(answer):
    assert is_affirmative(answer)


@pytest.mark.parametrize("answer", ["", "nu", "Nu", "nimic", "-"])
def test_is_negative(answer):
    assert is_negative(answer)


def test_free_text_is_neither_affirmative_nor_negative():
    answer = "luna 90 e invalidă"
    assert not is_affirmative(answer)
    assert not is_negative(answer)


def test_list_test_names_finds_only_test_functions():
    code = "def helper(): pass\ndef test_a(): pass\nclass TestX:\n    def test_b(self): pass\n"
    assert list_test_names(code) == ["test_a", "test_b"]


def test_list_test_names_on_invalid_code_returns_empty():
    assert list_test_names("def (:") == []


def test_syntax_error_reports_line():
    assert syntax_error("x = 1\ndef (:").startswith("linia 2")
    assert syntax_error("x = 1") is None


def test_truncate_keeps_the_end():
    text = "a" * 100 + "EROARE"
    result = truncate(text, max_chars=10)
    assert result.endswith("EROARE")
    assert "trunchiat" in result
    assert truncate("scurt", max_chars=10) == "scurt"
