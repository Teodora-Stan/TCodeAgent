"""
The LLM access layer: ALL calls to the model go through the functions here.

Benefit: the nodes know nothing about Groq / LangChain. If you want another
provider (OpenAI, Ollama...), you only change `get_llm()`.

Fallback models: on Groq's free plan, every model has a DAILY token quota.
When the main model runs out, we automatically switch to the next one in
`SETTINGS.fallback_models` and don't try the exhausted one again until the end.
"""

import os
from functools import lru_cache
from typing import TypeVar

from groq import RateLimitError
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel

from config import SETTINGS
from utils.text import extract_code_block, strip_reasoning

# `T` = "any subclass of BaseModel". This way `ask_structured(TestReview, ...)`
# returns exactly a `TestReview` as far as the type checker is concerned.
T = TypeVar("T", bound=BaseModel)

# The models that ran out of daily quota during the current run.
_exhausted_models: set[str] = set()


class AllModelsExhaustedError(RuntimeError):
    """All models (main + fallbacks) have run out of daily quota."""


# ---------------------------------------------------------------- Clients


@lru_cache(maxsize=None)
def get_llm(model: str, temperature: float) -> ChatGroq:
    """Creates the LLM client (only once per model + temperature, thanks to the cache).

    ChatGroq reads the API key automatically from the GROQ_API_KEY environment variable.
    `max_retries` automatically retries on network errors / PER-MINUTE limits (429).
    """
    # Without a key, Groq sends an empty "Bearer " header and fails with a
    # hard-to-understand "Connection error" -> we check it ourselves first.
    if not os.getenv("GROQ_API_KEY", "").strip():
        raise RuntimeError(
            "GROQ_API_KEY lipsește sau e goală. Completează-o în fișierul .env "
            "(cheie de la https://console.groq.com/keys)."
        )
    return ChatGroq(
        model=model,
        temperature=temperature,
        max_retries=3,
        timeout=120,  # a single request can't block the agent for more than 2 minutes
        **model_specific_options(model),
    )


def model_specific_options(model: str) -> dict:
    """Options that only apply to some models.

    gpt-oss models "think" before answering, and the thinking tokens count
    towards the quota. `reasoning_effort="low"` reduces them considerably.
    """
    if model.startswith("openai/gpt-oss"):
        return {"reasoning_effort": SETTINGS.reasoning_effort}
    return {}


def candidate_models() -> list[str]:
    """The models to try, in order: the main one, then the non-exhausted fallbacks."""
    models = [SETTINGS.model, *SETTINGS.fallback_models]
    return [m for m in models if m not in _exhausted_models]


def is_daily_limit(error: RateLimitError) -> bool:
    """True if the 429 error is about the DAILY quota (tokens/requests per day).

    Per-minute limits go away on their own (the client waits and retries); daily
    ones don't, so that's the only case where switching models makes sense.
    """
    message = str(error)
    return "(TPD)" in message or "(RPD)" in message or "per day" in message


# ---------------------------------------------------------------- Call with fallback


def invoke_with_fallback(messages: list[BaseMessage], temperature: float, schema: type[T] | None = None):
    """Sends the messages to the first available model; on an exhausted daily quota, moves to the next.

    `schema=None` -> returns the raw message; otherwise -> the validated Pydantic object.
    """
    for model in candidate_models():
        llm = get_llm(model, temperature)
        runnable = llm.with_structured_output(schema) if schema else llm
        try:
            return runnable.invoke(messages)
        except RateLimitError as error:
            if not is_daily_limit(error):
                raise
            _exhausted_models.add(model)
            print(f"  ⚠ {model} și-a epuizat cota zilnică; încerc următorul model.", flush=True)

    raise AllModelsExhaustedError(
        "Toate modelele și-au epuizat cota zilnică Groq: "
        + ", ".join([SETTINGS.model, *SETTINGS.fallback_models])
        + ". Încearcă mai târziu sau adaugă alte modele în LLM_FALLBACK_MODELS."
    )


def _messages(system: str, user: str) -> list[BaseMessage]:
    """Builds the standard conversation: instructions (system) + the request (user).

    Also prints an indicator, so it's visible that the agent is waiting for the LLM (not stuck).
    """
    print("  ⋯ aștept răspunsul LLM...", flush=True)
    return [SystemMessage(content=system), HumanMessage(content=user)]


# ---------------------------------------------------------------- API used by the nodes


def ask_text(system: str, user: str, temperature: float = SETTINGS.temperature) -> str:
    """LLM call that returns free text (e.g. the final report in markdown)."""
    response = invoke_with_fallback(_messages(system, user), temperature)
    return strip_reasoning(str(response.content))


def ask_code(system: str, user: str, temperature: float = SETTINGS.temperature) -> str:
    """LLM call that returns ONLY the Python code from the first ```python``` block."""
    return extract_code_block(ask_text(system, user, temperature))


def ask_structured(
    schema: type[T], system: str, user: str, temperature: float = SETTINGS.judge_temperature
) -> T:
    """LLM call that returns a validated Pydantic object (e.g. `TestReview`).

    `with_structured_output` sends the schema to the model as a "tool" and parses
    the response; if the JSON doesn't match the schema, it raises an exception.
    """
    return invoke_with_fallback(_messages(system, user), temperature, schema)
