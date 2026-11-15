# Rola pliku: Rejestr zadań AI; nazwa zadania z wejścia wybiera funkcję `run(input, ctx)`.

from ai.tasks import article, auto_fix, classify, embed, feedback, qa, research, wordpress

TASKS = {
    "classify": classify.run,
    "feedback.suggest": feedback.run,
    "embed": embed.run,
    "research.extract": research.extract,
    "research.discover": research.discover,
    "research.analyse": research.analyse,
    "article.brief": article.brief,
    "article.write": article.write,
    "article.rebuild": article.rebuild,
    "seo.preview": article.seo_preview,
    "qa.evaluate": qa.evaluate,
    "autofix.fix": auto_fix.fix,
    "seo.profile": wordpress.profile,
    "seo.prepare": wordpress.prepare,
    "wordpress.render": wordpress.render,
    "wordpress.metadata": wordpress.metadata,
    "wordpress.verify_meta": wordpress.verify_meta,
}
