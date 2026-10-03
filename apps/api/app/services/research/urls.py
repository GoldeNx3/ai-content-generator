# Rola pliku: Normalizuje adresy URL i wydobywa domeny, tak aby porównywanie źródeł nie zależało od
# części różnic w zapisie adresu.

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PREFIXES = ("utm_", "mc_", "fbclid", "gclid", "ref_src")
_SECOND_LEVEL = {"co", "com", "org", "net", "gov", "ac", "edu"}


# Do porównań usuwamy m.in. www, fragment i parametry śledzące; to klucz deduplikacji, nie sprawdzenie
# dostępności strony.
def normalize_url(url: str) -> str:
    """Canonical form used for deduplication and for matching LLM references."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if parts.port and parts.port not in (80, 443):
        host = f"{host}:{parts.port}"
    query = urlencode(
        [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith(_TRACKING_PREFIXES)]
    )
    path = parts.path.rstrip("/") or ""
    return urlunsplit(("https" if parts.scheme in ("http", "https") else parts.scheme, host, path, query, ""))


# urlsplit rozdziela adres na części; hostname zawiera sam host, bez ścieżki i parametrów.
def hostname(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


# To przybliżenie domeny głównej z wyjątkami typu co.uk, a nie pełny parser public suffix list.
def registered_domain(url_or_host: str) -> str:
    """Approximate eTLD+1 (example.co.uk, openai.com) without extra dependencies."""
    host = hostname(url_or_host) if "/" in url_or_host else url_or_host.lower()
    labels = [label for label in host.split(".") if label]
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in _SECOND_LEVEL:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])
