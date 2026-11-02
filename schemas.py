"""
Scheme Pydantic pentru răspunsurile STRUCTURATE ale LLM-ului.

Când îi cerem modelului un răspuns de forma uneia dintre aceste clase,
LangChain (`with_structured_output`) validează automat JSON-ul primit și ne dă
direct un obiect Python tipat. Descrierile (`Field(description=...)`) ajung în
schema trimisă modelului, deci sunt de fapt și instrucțiuni pentru el.

Codul (teste / implementare) NU trece prin scheme: e cerut ca text simplu într-un
bloc ```python```, pentru că modelele greșesc mai des când trebuie să escape-uiască
cod lung în interiorul unui JSON.
"""

from typing import Literal

from pydantic import BaseModel, Field


class TaskUnderstanding(BaseModel):
    """Cum a înțeles agentul cerința (folosit de nodul clarify_task)."""

    summary: str = Field(description="Reformularea cerinței în 2-4 propoziții, în română.")
    interface: list[str] = Field(
        description="Semnăturile funcțiilor/claselor propuse, ex: 'def slugify(text: str) -> str'."
    )
    assumptions: list[str] = Field(description="Presupunerile făcute acolo unde cerința e ambiguă.")
    open_questions: list[str] = Field(
        default_factory=list,
        description="Întrebări pentru utilizator, doar dacă ceva e cu adevărat neclar.",
    )


class TestReview(BaseModel):
    """Verdictul criticului pe suita de teste (nodul judge_tests)."""

    approved: bool = Field(description="True dacă suita e suficient de bună pentru a începe implementarea.")
    score: int = Field(ge=1, le=10, description="Calitatea suitei, de la 1 (slabă) la 10 (excelentă).")
    missing_cases: list[str] = Field(
        default_factory=list, description="Cazuri importante care NU sunt testate."
    )
    problems: list[str] = Field(
        default_factory=list,
        description="Teste greșite: valori așteptate incorecte, aserțiuni slabe, dependențe fragile.",
    )


class TestVerdict(BaseModel):
    """Verdictul pentru UN test picat: de vină e codul sau testul?"""

    test_name: str = Field(description="Numele testului picat, exact ca în lista primită.")
    # `Literal` = câmpul poate avea DOAR una dintre aceste două valori.
    culprit: Literal["code", "test"] = Field(
        description="'test' DOAR dacă ești sigur că valoarea așteptată din test contrazice cerința; altfel 'code'."
    )
    reason: str = Field(description="Justificarea, cu calculul făcut pas cu pas, în română.")
    corrected_expectation: str = Field(
        default="",
        description="Dacă culprit='test': ce ar trebui să aștepte testul (ex: \"validate_cnp('...') -> False\").",
    )


class FailureDiagnosis(BaseModel):
    """Diagnosticul pentru toate testele picate la o rulare (nodul diagnose_failure)."""

    verdicts: list[TestVerdict] = Field(description="Câte un verdict pentru fiecare test picat.")


class CodeReview(BaseModel):
    """Verdictul criticului pe cod, după ce testele au trecut (nodul judge_code)."""

    approved: bool = Field(description="False DOAR dacă există probleme care chiar merită o nouă iterație.")
    blocking_issues: list[str] = Field(
        default_factory=list,
        description="Probleme serioase: bug-uri netestate, complexitate inutilă, cod duplicat, nume confuze.",
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Îmbunătățiri opționale (nu blochează aprobarea)."
    )
