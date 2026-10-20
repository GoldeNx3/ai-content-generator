# Rola pliku: Rejestr zadań AI; nazwa zadania z wejścia wybiera funkcję `run(input, ctx)`.

from ai.tasks import article, classify, qa, research

TASKS = {
    "classify": classify.run,
    "research.extract": research.extract,
    "research.discover": research.discover,
    "research.analyse": research.analyse,
    "article.brief": article.brief,
    "article.write": article.write,
    "article.rebuild": article.rebuild,
    "seo.preview": article.seo_preview,
    "qa.evaluate": qa.evaluate,
}
