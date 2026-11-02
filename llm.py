"""
Stratul de acces la LLM: TOATE apelurile către model trec prin funcțiile de aici.

Avantaj: nodurile nu știu nimic despre Groq / LangChain. Dacă vrei alt provider
(OpenAI, Ollama...), schimbi doar `get_llm()`.

Modele de rezervă: pe planul gratuit Groq, fiecare model are o cotă ZILNICĂ de
tokeni. Când modelul principal o epuizează, trecem automat la următorul din
`SETTINGS.fallback_models` și nu-l mai încercăm pe cel epuizat până la final.
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

# `T` = "orice subclasă de BaseModel". Așa `ask_structured(TestReview, ...)`
# întoarce, pentru type checker, exact un `TestReview`.
T = TypeVar("T", bound=BaseModel)

# Modelele care și-au epuizat cota zilnică în rularea curentă.
_exhausted_models: set[str] = set()


class AllModelsExhaustedError(RuntimeError):
    """Toate modelele (principal + rezervă) și-au epuizat cota zilnică."""


# ---------------------------------------------------------------- Clienți


@lru_cache(maxsize=None)
def get_llm(model: str, temperature: float) -> ChatGroq:
    """Creează (o singură dată per model + temperatură, datorită cache-ului) clientul LLM.

    Cheia API e citită automat de ChatGroq din variabila de mediu GROQ_API_KEY.
    `max_retries` reîncearcă automat la erori de rețea / limite PE MINUT (429).
    """
    # Fără cheie, Groq trimite header-ul "Bearer " gol și eșuează cu un
    # "Connection error" greu de înțeles -> verificăm noi înainte.
    if not os.getenv("GROQ_API_KEY", "").strip():
        raise RuntimeError(
            "GROQ_API_KEY lipsește sau e goală. Completează-o în fișierul .env "
            "(cheie de la https://console.groq.com/keys)."
        )
    return ChatGroq(
        model=model,
        temperature=temperature,
        max_retries=3,
        timeout=120,  # un singur request nu poate bloca agentul mai mult de 2 minute
        **model_specific_options(model),
    )


def model_specific_options(model: str) -> dict:
    """Opțiuni valabile doar pentru unele modele.

    Modelele gpt-oss "gândesc" înainte să răspundă, iar tokenii de gândire se
    numără la cotă. `reasoning_effort="low"` îi reduce considerabil.
    """
    if model.startswith("openai/gpt-oss"):
        return {"reasoning_effort": SETTINGS.reasoning_effort}
    return {}


def candidate_models() -> list[str]:
    """Modelele de încercat, în ordine: principalul, apoi rezervele neepuizate."""
    models = [SETTINGS.model, *SETTINGS.fallback_models]
    return [m for m in models if m not in _exhausted_models]


def is_daily_limit(error: RateLimitError) -> bool:
    """True dacă eroarea 429 e pentru cota ZILNICĂ (tokens/requests per day).

    Limitele pe minut trec singure (clientul așteaptă și reîncearcă); cele pe zi
    nu, deci doar atunci are sens să schimbăm modelul.
    """
    message = str(error)
    return "(TPD)" in message or "(RPD)" in message or "per day" in message


# ---------------------------------------------------------------- Apel cu rezervă


def invoke_with_fallback(messages: list[BaseMessage], temperature: float, schema: type[T] | None = None):
    """Trimite mesajele la primul model disponibil; la cotă zilnică epuizată, trece la următorul.

    `schema=None` -> întoarce mesajul brut; altfel -> obiectul Pydantic validat.
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
    """Construiește conversația standard: instrucțiuni (system) + cererea (user).

    Afișează și un indicator, ca să se vadă că agentul așteaptă LLM-ul (nu e blocat).
    """
    print("  ⋯ aștept răspunsul LLM...", flush=True)
    return [SystemMessage(content=system), HumanMessage(content=user)]


# ---------------------------------------------------------------- API folosit de noduri


def ask_text(system: str, user: str, temperature: float = SETTINGS.temperature) -> str:
    """Apel LLM care întoarce text liber (ex: raportul final în markdown)."""
    response = invoke_with_fallback(_messages(system, user), temperature)
    return strip_reasoning(str(response.content))


def ask_code(system: str, user: str, temperature: float = SETTINGS.temperature) -> str:
    """Apel LLM care întoarce DOAR codul Python din primul bloc ```python```."""
    return extract_code_block(ask_text(system, user, temperature))


def ask_structured(
    schema: type[T], system: str, user: str, temperature: float = SETTINGS.judge_temperature
) -> T:
    """Apel LLM care întoarce un obiect Pydantic validat (ex: `TestReview`).

    `with_structured_output` trimite schema ca "tool" modelului și parsează
    răspunsul; dacă JSON-ul nu respectă schema, aruncă o excepție.
    """
    return invoke_with_fallback(_messages(system, user), temperature, schema)
