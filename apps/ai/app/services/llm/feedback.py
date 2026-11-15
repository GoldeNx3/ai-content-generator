# Rola pliku: Prompt i dostawca LLM pętli zwrotnej: z poprawek redaktora i powodów odrzuceń wyciąga ogólne zasady
# stylu i zakazane zwroty do profilu redakcji. Propozycje trafiają do profilu dopiero po akceptacji redaktora.

import json

from app.schemas.editorial import EditorialProfile
from app.schemas.feedback import FeedbackSuggestions
from app.services.llm.client import OpenAIClient

FEEDBACK_SYSTEM_PROMPT = """\
Jesteś redaktorem prowadzącym polskiego bloga technologicznego. Dostajesz fragmenty tekstu napisanego przez AI
(„przed”) i ten sam fragment po ręcznej poprawce redaktora („po”) oraz powody, dla których redaktor odrzucał wersje.
Twoje zadanie: zaproponować do 8 OGÓLNYCH zasad, dzięki którym kolejne teksty nie będą wymagały takich poprawek.

Rodzaje propozycji:
- style_rule: krótka zasada stylu w trybie rozkazującym (do 200 znaków), np. „Pierwsze zdanie podaje konkretny fakt
  z datą, bez ogólnego wstępu.”
- banned_phrase: dosłowny zwrot (do 80 znaków), który redaktor konsekwentnie usuwa.

Zasady:
- Uogólniaj wzorzec, nie opisuj jednej konkretnej zmiany treści ani faktu (poprawka liczby to nie zasada stylu).
- Proponuj tylko to, co wynika z co najmniej jednej poprawki lub powodu odrzucenia; w `why` wskaż, z czego wynika.
- Nie powtarzaj zasad i zwrotów, które są już w aktualnym profilu.
- Brak wyraźnego wzorca = pusta lista. Lepiej mniej, ale trafnie.
- Pisz po polsku."""


def build_feedback_prompt(title: str, passages: list[dict[str, str]], rejections: list[str],
                          profile: EditorialProfile | None) -> str:
    profile = profile or EditorialProfile()
    current = {
        "zakazane_zwroty": [f"„{phrase}”" for phrase in profile.banned_phrases],
        "zasady_stylu": profile.style_rules,
    }
    return (
        f"TEMAT ARTYKUŁU: {title}\n\n"
        f"POPRAWKI REDAKTORA (przed → po):\n{json.dumps(passages, ensure_ascii=False, indent=1)}\n\n"
        f"POWODY ODRZUCENIA WERSJI:\n{json.dumps(rejections, ensure_ascii=False)}\n\n"
        f"AKTUALNY PROFIL (nie powtarzaj):\n{json.dumps(current, ensure_ascii=False)}"
    )


class OpenAIFeedback:
    def __init__(self, client: OpenAIClient, model: str, timeout: float = 120) -> None:
        self.client, self.model, self.timeout = client, model, timeout

    async def suggest(self, prompt: str) -> FeedbackSuggestions:
        parsed, usage = await self.client.parse(self.model, FEEDBACK_SYSTEM_PROMPT, prompt, FeedbackSuggestions, timeout=self.timeout)
        parsed._usage = ({"model": usage.model, "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
                          "response_id": usage.response_id} if usage.recorded else None)
        return parsed
