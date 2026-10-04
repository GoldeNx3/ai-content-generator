"""Opt-in paid smoke check: python -m tests.qa_live_check ARTICLE_ID.

Uses an existing article's research snapshot and a synthetic corrupted draft.
Never edits the article, fetches URLs or runs new research.
"""
import asyncio
import json
import sys
from copy import deepcopy

from app.core.config import get_settings
from app.core.db import get_session_factory
from app.models import Article
from app.services.qa.context import build_qa_payload
from app.services.qa.validation import validate_output, validate_references, calculate_scores
from app.services.llm.client import OpenAIClient
from app.services.llm.qa import OpenAIQA
from app.services.llm.cost import LLMCostCalculator


async def main(article_id):
    settings = get_settings()
    async with get_session_factory()() as session:
        article = await session.get(Article, article_id)
        payload = deepcopy(build_qa_payload(article))
    # The stored facts suffice for this negative fixture; omit long source bodies to limit cost.
    for source in payload['research']['sources']:
        source['content'] = ''
    payload['article'].update(title='Zmiany w SvelteKit 3', lead='SvelteKit 3 jest dostępny.',
        content='''## Wydajność
SvelteKit 3 przyspiesza budowanie o 47%.

## Cytat
Rich Harris powiedział: „Każda aplikacja działa dwa razy szybciej”.

## Premiera
SvelteKit 3 wydano 1 października 2025 r.

## Stare API
Stara nazwa `$app/environment` z całą pewnością przestała być dostępna w wersji 3.

## Stabilizacja
Remote functions i Async Svelte będą stabilne 1 listopada 2026 r.
''', sections=[], lead_fact_ids=[], meta_title='Zmiany w SvelteKit 3',
        meta_description='Wymagania i zmiany w SvelteKit 3.')
    client = OpenAIClient(settings.openai_api_key, max_retries=0)
    try:
        result = await OpenAIQA(client, settings.qa_model, settings.qa_timeout_seconds).evaluate(payload)
        from pathlib import Path
        Path('/tmp/qa-live-raw.json').write_text(json.dumps(dict(payload=payload,
            output=result.output.model_dump(mode='json')), ensure_ascii=False))
        output = validate_output(result.output, payload, validate_references(payload))
        scores = calculate_scores(output, settings.qa_pass_score)
        findings = [i.model_dump(mode='json') for i in output.issues]
        print(json.dumps(dict(scores=scores, issues=findings, model=result.usage.model,
            input_tokens=result.usage.input_tokens, output_tokens=result.usage.output_tokens,
            cost=str(LLMCostCalculator(settings.llm_pricing).estimate(result.usage.model,
                result.usage.input_tokens, result.usage.output_tokens))), ensure_ascii=False))
        for marker in ['47%', 'Rich Harris', '2025', '$app/environment', '1 listopada 2026']:
            assert any(marker in i.excerpt and i.type not in ('style_issue','structure_issue','seo_issue')
                       for i in output.issues), f'Missing factual finding: {marker}'
        assert any(i.type == 'unsupported_quote' and i.severity == 'critical' for i in output.issues)
        assert not scores['qa_passed'] and scores['overall_score'] <= 60
        print('PASS: actual LLM detects number, attributed quote, date, conflicting API claim and uncertain timeline.')
    finally:
        await client._client.close()


if __name__ == '__main__':
    asyncio.run(main(int(sys.argv[1])))
