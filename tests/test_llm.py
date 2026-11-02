"""Tests for the automatic switch to fallback models in llm.py (no real calls)."""

import httpx
import pytest
from groq import RateLimitError

import llm
from config import SETTINGS


def rate_limit(message: str) -> RateLimitError:
    """A fake 429 error with the given message."""
    request = httpx.Request("POST", "https://api.groq.com")
    return RateLimitError(message, response=httpx.Response(429, request=request), body=None)


DAILY = rate_limit("Rate limit reached on tokens per day (TPD)")
PER_MINUTE = rate_limit("Rate limit reached on tokens per minute (TPM)")


class FakeModel:
    """Fake model: raises the given error or returns its own name."""

    def __init__(self, name: str, error: Exception | None, calls: list[str]):
        self.name, self.error, self.calls = name, error, calls

    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        self.calls.append(self.name)
        if self.error:
            raise self.error
        return self.name


@pytest.fixture
def fake_models(monkeypatch):
    """Replaces get_llm; `errors` = {model: error} for the models that should fail."""
    monkeypatch.setattr(llm, "_exhausted_models", set())
    errors: dict[str, Exception] = {}
    calls: list[str] = []
    monkeypatch.setattr(llm, "get_llm", lambda model, temperature: FakeModel(model, errors.get(model), calls))
    return errors, calls


def test_uses_main_model_when_available(fake_models):
    assert llm.invoke_with_fallback([], 0.0) == SETTINGS.model


def test_daily_limit_falls_back_and_remembers(fake_models):
    errors, calls = fake_models
    errors[SETTINGS.model] = DAILY
    first_fallback = SETTINGS.fallback_models[0]

    assert llm.invoke_with_fallback([], 0.0) == first_fallback
    calls.clear()
    # The second call doesn't try the exhausted model again.
    assert llm.invoke_with_fallback([], 0.0) == first_fallback
    assert calls == [first_fallback]


def test_per_minute_limit_is_not_a_fallback_reason(fake_models):
    errors, _ = fake_models
    errors[SETTINGS.model] = PER_MINUTE
    with pytest.raises(RateLimitError):
        llm.invoke_with_fallback([], 0.0)


def test_all_models_exhausted_raises_clear_error(fake_models):
    errors, _ = fake_models
    for model in [SETTINGS.model, *SETTINGS.fallback_models]:
        errors[model] = DAILY
    with pytest.raises(llm.AllModelsExhaustedError):
        llm.invoke_with_fallback([], 0.0)
