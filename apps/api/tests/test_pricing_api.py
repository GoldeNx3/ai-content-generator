async def test_pricing_exposes_public_configuration_without_secrets(client) -> None:
    response = await client.get("/api/pricing")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"models", "rates", "source_url", "verified_at"}
    assert set(body["models"]) == {"classifier", "research", "brief", "writer", "qa", "auto_fix"}
    assert body["rates"]["gpt-4.1-mini"]["input"] == 0.4
    assert body["rates"]["gpt-6.1-sol"]["output"] == 10
