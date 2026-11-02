"""
Configurația agentului (modelul LLM + limitele buclelor).

Toate valorile pot fi suprascrise din variabile de mediu (sau dintr-un fișier
`.env`), ca să nu modifici codul când vrei să experimentezi cu alte limite.
"""

import os
from dataclasses import dataclass
from pathlib import Path

# python-dotenv e opțional: dacă e instalat, citim `.env` din directorul curent.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _env_int(name: str, default: int) -> int:
    """Citește un întreg din mediu; dacă variabila lipsește, întoarce `default`."""
    return int(os.getenv(name, default))


def _env_list(name: str, default: str) -> tuple[str, ...]:
    """Citește o listă separată prin virgulă (ex: "a,b,c" -> ("a", "b", "c"))."""
    return tuple(item.strip() for item in os.getenv(name, default).split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    """Setările agentului. `frozen=True` => nu pot fi modificate accidental la rulare."""

    # --- LLM ---
    model: str                      # modelul principal pe Groq
    fallback_models: tuple[str, ...]  # modele de rezervă când cel principal își termină cota zilnică
    reasoning_effort: str           # "low" / "medium" / "high" pentru modelele gpt-oss (mai mic = mai puțini tokeni)
    temperature: float              # temperatura pentru generare (cod / teste)
    judge_temperature: float        # temperatura pentru critici (mai mică = mai consecvent)

    # --- Faza de teste ---
    max_test_judge_iterations: int  # de câte ori poate respinge criticul testele

    # --- Faza de cod ---
    max_fix_attempts: int           # câte rulări picate de teste tolerăm în total
    max_same_test_failures: int     # de câte ori la rând poate pica ACELAȘI test
    max_refine_iterations: int      # câte runde de îmbunătățiri cerute de criticul de cod
    max_test_repairs: int           # de câte ori pot fi corectate testele suspectate ca greșite

    # --- Execuție ---
    test_timeout_seconds: int       # timeout pentru pytest (protecție la bucle infinite)
    output_dir: Path                # unde salvăm codul, testele și raportul final
    checkpoint_db: Path             # baza SQLite cu starea salvată după fiecare nod (pentru reluare)


def load_settings() -> Settings:
    """Construiește obiectul `Settings` din variabilele de mediu (cu valori implicite)."""
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


# Instanța globală folosită de restul modulelor: `from config import SETTINGS`.
SETTINGS = load_settings()
