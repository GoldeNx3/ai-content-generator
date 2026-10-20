# Rola pliku: Modele tabel enums: mapują rekordy SQL na obiekty Pythona i definiują pola oraz powiązania.

from enum import StrEnum


class SourceType(StrEnum):
    RSS = "rss"


class CandidateStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    IGNORED = "ignored"


class CandidateCategory(StrEnum):
    NEWS = "news"
    GUIDE = "guide"
    COMPARISON = "comparison"
    PRICING = "pricing"
    RELEASE = "release"
    TOOL = "tool"
    OTHER = "other"


class ResearchStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchSourceType(StrEnum):
    OFFICIAL = "official"
    DOCUMENTATION = "documentation"
    GITHUB = "github"
    NEWS = "news"
    BLOG = "blog"
    COMMUNITY = "community"
    OTHER = "other"


class ResearchSourceOrigin(StrEnum):
    ORIGINAL = "original"  # Candidate.external_url
    SEARCH = "search"  # found by SearchProvider
    MANUAL = "manual"  # added by the user


class FetchStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class ArticleStatus(StrEnum):
    NEEDS_CHANGES = "needs_changes"
    READY_FOR_APPROVAL = "ready_for_approval"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    SUPERSEDED = "superseded"
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"


class FactBasis(StrEnum):
    VERIFIABLE = "verifiable"  # objective fact stated by a primary source
    VENDOR_CLAIM = "vendor_claim"  # company's own claim about its product (benchmarks, "3x faster")
    SECONDARY = "secondary"  # only reported by third parties / imprecise


class FactImportance(StrEnum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    SUPPORTING = "supporting"


class AuthAttemptKind(StrEnum):
    LOGIN = "login"
    REGISTER = "register"


class WorkspaceRole(StrEnum):
    OWNER = "owner"
    MEMBER = "member"
