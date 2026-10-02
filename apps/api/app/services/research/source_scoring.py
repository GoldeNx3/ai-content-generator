"""Backend heuristic for source type and credibility score.

The LLM may *suggest* a type for unknown domains, but the score always comes from here.
Note: number of sources is never treated as proof - this only ranks individual sources.
"""

from dataclasses import dataclass

from app.models import ResearchSourceType
from app.services.research.urls import hostname, registered_domain

SCORE_OFFICIAL = 100
SCORE_DOCUMENTATION = 100
SCORE_OFFICIAL_GITHUB = 95
SCORE_GOV_EDU = 95
SCORE_WIRE_AGENCY = 90
SCORE_TECH_PUBLICATION = 80
SCORE_SPECIALIST_BLOG = 65
SCORE_COMMUNITY = 50
SCORE_UNKNOWN = 40

WIRE_AGENCIES = {"reuters.com", "apnews.com"}
TECH_PUBLICATIONS = {
    "theverge.com", "techcrunch.com", "arstechnica.com", "wired.com", "venturebeat.com",
    "zdnet.com", "engadget.com", "theregister.com", "bloomberg.com", "ft.com", "nytimes.com",
    "wsj.com", "theinformation.com", "cnbc.com", "bbc.co.uk", "bbc.com", "theguardian.com",
    "technologyreview.com", "infoq.com", "9to5google.com", "9to5mac.com", "macrumors.com",
    "tomshardware.com", "axios.com", "semafor.com", "spidersweb.pl", "antyweb.pl",
    "benchmark.pl", "chip.pl", "komputerswiat.pl", "geekweek.interia.pl",
}
COMMUNITY = {
    "reddit.com", "news.ycombinator.com", "ycombinator.com", "x.com", "twitter.com",
    "stackoverflow.com", "stackexchange.com", "discord.com", "discord.gg", "threads.net",
    "facebook.com", "linkedin.com", "youtube.com", "quora.com", "lemmy.world", "bsky.app",
}
BLOG_PLATFORMS = {"medium.com", "substack.com", "dev.to", "hashnode.dev", "blogspot.com", "wordpress.com"}
GOV_EDU_SUFFIXES = (".gov", ".edu", ".mil", ".gov.pl", ".edu.pl", ".ac.uk", ".gov.uk", ".europa.eu")
DOC_HOST_PREFIXES = ("docs.", "developer.", "developers.", "dev.", "learn.", "platform.", "api.", "help.", "support.")
DOC_PATH_MARKERS = ("/docs", "/documentation", "/reference", "/api-reference", "/guides")
TYPE_SCORES = {
    ResearchSourceType.OFFICIAL: SCORE_OFFICIAL,
    ResearchSourceType.DOCUMENTATION: SCORE_DOCUMENTATION,
    ResearchSourceType.GITHUB: SCORE_OFFICIAL_GITHUB,
    ResearchSourceType.NEWS: SCORE_TECH_PUBLICATION,
    ResearchSourceType.BLOG: SCORE_SPECIALIST_BLOG,
    ResearchSourceType.COMMUNITY: SCORE_COMMUNITY,
    ResearchSourceType.OTHER: SCORE_UNKNOWN,
}
# Cap for types suggested by the LLM for domains the heuristic does not recognise.
LLM_SUGGESTION_MAX_SCORE = SCORE_SPECIALIST_BLOG


@dataclass(frozen=True, slots=True)
class SourceAssessment:
    source_type: ResearchSourceType
    score: int
    recognized: bool


def assess_source(url: str, official_domains: set[str]) -> SourceAssessment:
    """official_domains: registered domains of the company behind the topic (e.g. {"openai.com"})."""
    host = hostname(url)
    domain = registered_domain(host)
    path = url.lower()

    if domain == "github.com" or host.endswith("github.io"):
        owner = _github_owner(url, host)
        is_official = bool(owner) and any(owner == official.split(".")[0] for official in official_domains)
        return SourceAssessment(
            ResearchSourceType.GITHUB, SCORE_OFFICIAL_GITHUB if is_official else SCORE_SPECIALIST_BLOG, True
        )
    if _is_official(domain, official_domains):
        is_docs = host.startswith(DOC_HOST_PREFIXES) or any(marker in path for marker in DOC_PATH_MARKERS)
        if is_docs:
            return SourceAssessment(ResearchSourceType.DOCUMENTATION, SCORE_DOCUMENTATION, True)
        return SourceAssessment(ResearchSourceType.OFFICIAL, SCORE_OFFICIAL, True)
    if host.endswith(GOV_EDU_SUFFIXES):
        return SourceAssessment(ResearchSourceType.OFFICIAL, SCORE_GOV_EDU, True)
    if domain in WIRE_AGENCIES:
        return SourceAssessment(ResearchSourceType.NEWS, SCORE_WIRE_AGENCY, True)
    if domain in TECH_PUBLICATIONS or host in TECH_PUBLICATIONS:
        return SourceAssessment(ResearchSourceType.NEWS, SCORE_TECH_PUBLICATION, True)
    if domain in COMMUNITY or host in COMMUNITY:
        return SourceAssessment(ResearchSourceType.COMMUNITY, SCORE_COMMUNITY, True)
    if domain in BLOG_PLATFORMS:
        return SourceAssessment(ResearchSourceType.BLOG, SCORE_SPECIALIST_BLOG, True)
    return SourceAssessment(ResearchSourceType.OTHER, SCORE_UNKNOWN, False)


# Platforms hosting content of other organisations under /<org>/... paths.
ORG_HOSTING_PLATFORMS = {"huggingface.co": ("blog/", ""), "github.com": ("",)}
RESERVED_PATH_SEGMENTS = {
    "blog", "docs", "datasets", "spaces", "models", "papers", "learn", "api", "collections",
    "orgs", "topics", "features", "settings", "marketplace", "sponsors", "enterprise", "pricing",
}


def official_domains_for(article_url: str) -> set[str]:
    """Domains (or org names) treated as official for a topic.

    - the candidate's own article domain, unless it is a known media/community site;
    - for posts hosted on platforms (huggingface.co/blog/<org>/..., github.com/<org>/...) also the
      org name, so e.g. allenai.org and github.com/allenai count as official for an Ai2 post.
    """
    domain = registered_domain(article_url)
    host = hostname(article_url)
    third_party = WIRE_AGENCIES | TECH_PUBLICATIONS | COMMUNITY | BLOG_PLATFORMS | {"github.com", "githubusercontent.com"}
    official: set[str] = set()
    if domain and domain not in third_party and host not in third_party:
        official.add(domain)
    owner = _platform_owner(article_url, domain)
    if owner:
        official.add(owner)
    return official


def _platform_owner(url: str, domain: str) -> str:
    prefixes = ORG_HOSTING_PLATFORMS.get(domain)
    if not prefixes:
        return ""
    path = url.split(domain, 1)[-1].lstrip("/")
    for prefix in prefixes:
        if path.startswith(prefix):
            parts = [part for part in path[len(prefix):].split("/") if part]
            if len(parts) >= 2 and parts[0].lower() not in RESERVED_PATH_SEGMENTS:  # <org>/<item>
                return parts[0].lower()
    return ""


def _is_official(domain: str, official: set[str]) -> bool:
    """official holds registered domains (openai.com) and bare org names (allenai)."""
    return domain in official or domain.split(".")[0] in official


def apply_llm_suggestion(current: SourceAssessment, suggested: ResearchSourceType) -> SourceAssessment:
    """LLM hints only refine unrecognised sources and can never lift them to 'official' scores."""
    if current.recognized or suggested == ResearchSourceType.OTHER:
        return current
    return SourceAssessment(suggested, min(TYPE_SCORES[suggested], LLM_SUGGESTION_MAX_SCORE), False)


def _github_owner(url: str, host: str) -> str:
    if host.endswith("github.io"):
        return host.split(".")[0]
    parts = [part for part in url.split("github.com/", 1)[-1].split("/") if part]
    return parts[0].lower() if parts else ""
