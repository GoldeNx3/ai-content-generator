# Rola pliku: Tryb demo: zarezerwowana przestrzeń URL kandydatów i zerowy cennik modelu demo.
DEMO_PREFIX = 'https://demo.content-engine.invalid/'
DEMO_MODEL = 'demo-static'



def demo_settings(settings):
    result = dict(settings)
    for field in ('openai_classifier_model', 'openai_research_model', 'openai_brief_model',
                  'openai_writer_model', 'openai_qa_model', 'openai_auto_fix_model'):
        result[field] = DEMO_MODEL
    result['llm_pricing'] = {DEMO_MODEL: {'input': 0, 'output': 0}}
    return result
