"""
Pydantic schemas for the LLM's STRUCTURED responses.

When we ask the model for a response shaped like one of these classes,
LangChain (`with_structured_output`) automatically validates the JSON it returns
and gives us a typed Python object directly. The descriptions (`Field(description=...)`)
end up in the schema sent to the model, so they are also instructions for it
(that's why they are in Romanian, like the rest of the prompts).

Code (tests / implementation) does NOT go through schemas: it's requested as plain
text in a ```python``` block, because models make more mistakes when they have to
escape long code inside a JSON string.
"""

from typing import Literal

from pydantic import BaseModel, Field


class TaskUnderstanding(BaseModel):
    """How the agent understood the request (used by the clarify_task node)."""

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
    """The critic's verdict on the test suite (the judge_tests node)."""

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
    """The verdict for ONE failing test: is the code or the test at fault?"""

    test_name: str = Field(description="Numele testului picat, exact ca în lista primită.")
    # `Literal` = the field can hold ONLY one of these two values.
    culprit: Literal["code", "test"] = Field(
        description="'test' DOAR dacă ești sigur că valoarea așteptată din test contrazice cerința; altfel 'code'."
    )
    reason: str = Field(description="Justificarea, cu calculul făcut pas cu pas, în română.")
    corrected_expectation: str = Field(
        default="",
        description="Dacă culprit='test': ce ar trebui să aștepte testul (ex: \"validate_cnp('...') -> False\").",
    )


class FailureDiagnosis(BaseModel):
    """The diagnosis for all the tests that failed in a run (the diagnose_failure node)."""

    verdicts: list[TestVerdict] = Field(description="Câte un verdict pentru fiecare test picat.")


class CodeReview(BaseModel):
    """The critic's verdict on the code, after the tests passed (the judge_code node)."""

    approved: bool = Field(description="False DOAR dacă există probleme care chiar merită o nouă iterație.")
    blocking_issues: list[str] = Field(
        default_factory=list,
        description="Probleme serioase: bug-uri netestate, complexitate inutilă, cod duplicat, nume confuze.",
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Îmbunătățiri opționale (nu blochează aprobarea)."
    )
