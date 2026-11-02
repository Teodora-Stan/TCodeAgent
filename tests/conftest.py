"""
Shared fixtures for the tests.

No test makes real LLM calls: where an LLM is needed, the `ask_*`
functions are replaced (monkeypatch) with scripted responses.
"""

import dataclasses

import pytest

import nodes.final_report
from state import AgentState, initial_state


@pytest.fixture
def make_state():
    """State factory: `make_state(execution_passed=True)` = the initial state + the given changes."""

    def _make(**overrides) -> AgentState:
        return {**initial_state("task de test"), **overrides}

    return _make


@pytest.fixture(autouse=True)
def isolated_output(tmp_path, monkeypatch):
    """The final report is written to a temporary directory, not to the project's output/."""
    settings = dataclasses.replace(nodes.final_report.SETTINGS, output_dir=tmp_path / "output")
    monkeypatch.setattr(nodes.final_report, "SETTINGS", settings)
    return settings.output_dir
