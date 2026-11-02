"""
Agent configuration (the LLM model + the loop limits).

Every value can be overridden from environment variables (or from a `.env`
file), so you don't have to change the code to experiment with other limits.
"""

import os
from dataclasses import dataclass
from pathlib import Path

# python-dotenv is optional: if it's installed, we read `.env` from the current directory.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _env_int(name: str, default: int) -> int:
    """Reads an integer from the environment; returns `default` if the variable is missing."""
    return int(os.getenv(name, default))


def _env_list(name: str, default: str) -> tuple[str, ...]:
    """Reads a comma-separated list (e.g. "a,b,c" -> ("a", "b", "c"))."""
    return tuple(item.strip() for item in os.getenv(name, default).split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    """The agent's settings. `frozen=True` => they can't be changed by accident at runtime."""

    # --- LLM ---
    model: str                      # the main model on Groq
    fallback_models: tuple[str, ...]  # fallback models for when the main one runs out of daily quota
    reasoning_effort: str           # "low" / "medium" / "high" for gpt-oss models (lower = fewer tokens)
    temperature: float              # temperature for generation (code / tests)
    judge_temperature: float        # temperature for the critics (lower = more consistent)

    # --- Test phase ---
    max_test_judge_iterations: int  # how many times the critic may reject the tests

    # --- Code phase ---
    max_fix_attempts: int           # how many failed test runs we tolerate in total
    max_same_test_failures: int     # how many times in a row the SAME test may fail
    max_refine_iterations: int      # how many improvement rounds the code critic may request
    max_test_repairs: int           # how many times tests suspected to be wrong may be corrected

    # --- Execution ---
    test_timeout_seconds: int       # pytest timeout (protection against infinite loops)
    output_dir: Path                # where we save the code, the tests and the final report
    checkpoint_db: Path             # SQLite database with the state saved after each node (for resuming)


def load_settings() -> Settings:
    """Builds the `Settings` object from environment variables (with defaults)."""
    return Settings(
        model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"),
        fallback_models=_env_list("LLM_FALLBACK_MODELS", "openai/gpt-oss-20b,qwen/qwen3.8-27b"),
        reasoning_effort=os.getenv("LLM_REASONING_EFFORT", "low"),
        temperature=float(os.getenv("LLM_TEMPERATURE", 0.2)),
        judge_temperature=float(os.getenv("JUDGE_TEMPERATURE", 0.0)),
        max_test_judge_iterations=_env_int("MAX_TEST_JUDGE_ITERATIONS", 3),
        max_fix_attempts=_env_int("MAX_FIX_ATTEMPTS", 5),
        max_same_test_failures=_env_int("MAX_SAME_TEST_FAILURES", 3),
        max_refine_iterations=_env_int("MAX_REFINE_ITERATIONS", 2),
        max_test_repairs=_env_int("MAX_TEST_REPAIRS", 2),
        test_timeout_seconds=_env_int("TEST_TIMEOUT_SECONDS", 30),
        output_dir=Path(os.getenv("OUTPUT_DIR", "output")),
        checkpoint_db=Path(os.getenv("CHECKPOINT_DB", "checkpoints.sqlite")),
    )


# The global instance used by the other modules: `from config import SETTINGS`.
SETTINGS = load_settings()
