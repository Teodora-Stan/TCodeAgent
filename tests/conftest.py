"""
Fixture-uri comune pentru teste.

Niciun test nu face apeluri LLM reale: unde e nevoie de LLM, funcțiile
`ask_*` sunt înlocuite (monkeypatch) cu răspunsuri scriptate.
"""

import dataclasses

import pytest

import nodes.final_report
from state import AgentState, initial_state


@pytest.fixture
def make_state():
    """Fabrică de stări: `make_state(execution_passed=True)` = starea inițială + modificările date."""

    def _make(**overrides) -> AgentState:
        return {**initial_state("task de test"), **overrides}

    return _make


@pytest.fixture(autouse=True)
def isolated_output(tmp_path, monkeypatch):
    """Raportul final se scrie într-un director temporar, nu în output/ al proiectului."""
    settings = dataclasses.replace(nodes.final_report.SETTINGS, output_dir=tmp_path / "output")
    monkeypatch.setattr(nodes.final_report, "SETTINGS", settings)
    return settings.output_dir
