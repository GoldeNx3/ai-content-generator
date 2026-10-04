# Rola pliku: Testy modułu content_extractor: scenariusze poprawnego działania i błędów. Funkcje test_*
# odkrywa i uruchamia pytest.

import httpx
import pytest

from app.services.research import content_extractor
from app.services.research.content_extractor import ExtractionError
from tests.research_fakes import extractor_for, html_response

URL = "https://example.com/post"


# async def tworzy korutynę; await czeka na operację asynchroniczną i pozwala pętli zdarzeń obsługiwać
# inne zadania.
async def test_extracts_article_without_boilerplate() -> None:
    document = await extractor_for({URL: html_response("GPT-6 API released")}).extract(URL)

    assert "GPT-6 API to all developers" in document.content
    assert document.title == "GPT-6 API released"
    assert document.publisher == "Example Site"
    assert document.http_status == 200
    for boilerplate in ("Careers menu link", "cookies", "footer text", "sidebar story"):
        assert boilerplate not in document.content
    assert "<p>" not in document.content


async def test_empty_html_raises() -> None:
    extractor = extractor_for({URL: httpx.Response(200, text="", headers={"content-type": "text/html"})})

    with pytest.raises(ExtractionError, match="Empty page"):
        await extractor.extract(URL)


async def test_page_without_article_text_raises() -> None:
    html = "<html><body><nav>Home About</nav><footer>Footer</footer></body></html>"
    extractor = extractor_for({URL: httpx.Response(200, text=html, headers={"content-type": "text/html"})})

    with pytest.raises(ExtractionError, match="No meaningful"):
        await extractor.extract(URL)


async def test_http_404_raises_with_status() -> None:
    with pytest.raises(ExtractionError) as error:
        await extractor_for({}).extract(URL)

    assert error.value.http_status == 404


async def test_timeout_raises() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ExtractionError, match="Timeout"):
        await extractor_for({URL: timeout}).extract(URL)


async def test_non_html_content_is_rejected() -> None:
    response = httpx.Response(200, content=b"%PDF-1.7", headers={"content-type": "application/pdf"})

    with pytest.raises(ExtractionError, match="Unsupported content type"):
        await extractor_for({URL: response}).extract(URL)


async def test_falls_back_to_beautifulsoup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(content_extractor.trafilatura, "extract", lambda *args, **kwargs: None)

    document = await extractor_for({URL: html_response("Fallback title")}).extract(URL)

    assert document.method == "beautifulsoup"
    assert "GPT-6 API to all developers" in document.content
    for boilerplate in ("Careers menu link", "cookies", "footer text", "sidebar story"):
        assert boilerplate not in document.content


def test_trailing_related_section_is_removed() -> None:
    text = "Main paragraph. " * 40 + "\nRelated posts\nSome other article teaser"
    assert content_extractor._strip_trailing_boilerplate(text).endswith("Main paragraph.")


async def test_redirect_to_private_address_is_rejected_before_request():
    requests = []
    def respond(request):
        requests.append(str(request.url))
        if str(request.url) == URL:
            return httpx.Response(302, headers={'location': 'http://127.0.0.1/admin'})
        return html_response('Private resource')
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        extractor = content_extractor.ContentExtractor(client=client, resolve_dns=False)
        with pytest.raises(ExtractionError, match='public'):
            await extractor.extract(URL)
    assert requests == [URL]


async def test_private_dns_destination_is_rejected(monkeypatch):
    async def resolve(*args, **kwargs):
        return [(2, 1, 6, '', ('10.1.2.3', 443))]
    import asyncio
    monkeypatch.setattr(asyncio.get_running_loop(), 'getaddrinfo', resolve)
    extractor = content_extractor.ContentExtractor()
    with pytest.raises(ExtractionError, match='public'):
        await extractor.extract('https://private.example.com/article')


async def test_public_relative_redirect_preserves_extraction():
    redirected = 'https://example.com/final'
    extractor = extractor_for({
        URL: httpx.Response(301, headers={'location': '/final'}),
        redirected: html_response('Final article'),
    })
    document = await extractor.extract(URL)
    assert document.url == redirected
    assert document.title == 'Final article'


async def test_network_backend_connects_to_validated_ip_not_hostname(monkeypatch):
    from app.services.research.public_http import PublicNetworkBackend
    import asyncio
    queries, connections = [], []
    async def resolve(host, port, **kwargs):
        queries.append(host)
        return [(2, 1, 6, '', ('93.184.216.34', port))]
    class Backend:
        async def connect_tcp(self, host, port, **kwargs):
            connections.append(host)
            return 'stream'
    monkeypatch.setattr(asyncio.get_running_loop(), 'getaddrinfo', resolve)
    assert await PublicNetworkBackend(Backend()).connect_tcp('example.com', 443) == 'stream'
    assert queries == ['example.com']
    assert connections == ['93.184.216.34']
