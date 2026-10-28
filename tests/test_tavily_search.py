import pytest
from backend import tavily_search as ts


def test_parse_doorway_width_from_various_formats():
    # Meters
    assert ts.parse_doorway_width_from_text("Clear width must be at least 0.85 m for standard passage.") == 0.85
    # Millimeters
    assert ts.parse_doorway_width_from_text("Approved Document M specifies 800 mm clear opening.") == 0.80
    assert ts.parse_doorway_width_from_text("Australian standard AS 1428 requires 850mm.") == 0.85
    # Inches
    assert ts.parse_doorway_width_from_text("ADA Section 404 mandates 32 inches clear doorway.") == 0.813


def test_regional_doorway_spec_cached_fallback_when_offline(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr(ts, "TAVILY_API_KEY", "")
    us_spec = ts.fetch_regional_doorway_spec(region="US")
    assert us_spec["region"] == "US"
    assert us_spec["min_doorway_width_m"] == pytest.approx(0.813, rel=0.01)
    assert "cached_catalog" in us_spec["source"]

    uk_spec = ts.fetch_regional_doorway_spec(region="UK")
    assert uk_spec["region"] == "UK"
    assert uk_spec["min_doorway_width_m"] == 0.800
    assert "cached_catalog" in uk_spec["source"]

    eu_spec = ts.fetch_regional_doorway_spec(region="EU")
    assert eu_spec["region"] == "EU"
    assert eu_spec["min_doorway_width_m"] == 0.850

    au_spec = ts.fetch_regional_doorway_spec(region="AU")
    assert au_spec["region"] == "AU"
    assert au_spec["min_doorway_width_m"] == 0.850


def test_tavily_runtime_extraction_with_mock_client(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")

    class MockTavilyClient:
        def __init__(self, api_key):
            self.api_key = api_key

        def search(self, query, search_depth="basic", max_results=3):
            return {
                "results": [
                    {"content": "UK Building Regulations require an effective clear width of 825 mm for new accessible dwellings."}
                ]
            }

    import sys
    # Create fake tavily module
    import types
    fake_tavily = types.ModuleType("tavily")
    fake_tavily.TavilyClient = MockTavilyClient
    monkeypatch.setitem(sys.modules, "tavily", fake_tavily)

    spec = ts.fetch_regional_doorway_spec(region="UK")
    assert spec["source"] == "tavily_search_api"
    assert spec["min_doorway_width_m"] == 0.825
    assert spec["extracted_from_web"] is True


def test_tavily_parsing_failure_uses_cached_catalog_with_marked_source(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")

    class MockTavilyClientGibberish:
        def __init__(self, api_key): pass
        def search(self, **kw):
            return {"results": [{"content": "Architecture is the art and science of design without numerical specifications."}]}

    import sys, types
    fake_tavily = types.ModuleType("tavily")
    fake_tavily.TavilyClient = MockTavilyClientGibberish
    monkeypatch.setitem(sys.modules, "tavily", fake_tavily)

    spec = ts.fetch_regional_doorway_spec(region="EU")
    assert "cached_catalog" in spec["source"]
    assert "parsing_fallback" in spec["source"]
    assert spec["min_doorway_width_m"] == 0.850


def test_accessibility_search_endpoint_with_region(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr(ts, "TAVILY_API_KEY", "")
    from fastapi.testclient import TestClient
    from backend.main import app
    client = TestClient(app)

    r = client.post("/api/accessibility/search", json={"region": "UK", "query": "UK door width regulations"})
    assert r.status_code == 200
    data = r.json()
    assert data["region"] == "UK"
    assert data["min_doorway_width_m"] >= 0.75
    assert "source" in data
