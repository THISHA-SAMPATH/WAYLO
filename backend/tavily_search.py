import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Standard accessibility clearances catalog (ADA Title III & Architectural Standards)
STANDARD_ACCESSIBILITY_CLEARANCES = {
    "doorway": {
        "min_width_meters": 0.81,
        "standard_code": "ADA Title III Section 404.2.3",
        "guideline": "Clear opening width of doorways shall be 32 inches (815 mm / 0.81m) minimum."
    },
    "corridor": {
        "min_width_meters": 0.91,
        "standard_code": "ADA Title III Section 403.5.1",
        "guideline": "Clear width of an interior accessible route shall be 36 inches (915 mm / 0.91m) minimum."
    },
    "turning_radius": {
        "min_diameter_meters": 1.52,
        "standard_code": "ADA Title III Section 304.3.1",
        "guideline": "Space for a 60-inch (1525 mm) diameter circular turning space."
    },
    "ramp_slope": {
        "max_ratio": "1:12",
        "standard_code": "ADA Title III Section 405.2",
        "guideline": "Ramp runs shall have a running slope not steeper than 1:12 (8.33%)."
    }
}


class AccessibilityDict(dict):
    """Dictionary representation of accessibility standards context with string formatting fallback."""
    def __str__(self) -> str:
        return self.get("formatted_context", super().__str__())


def fetch_accessibility_context(query: str = "ADA doorway width standards") -> dict:
    """
    Fetches real-time spatial and accessibility standards context using Tavily Search API.
    Specifically checks for ADA Title III Section 404 (0.81m min clearance) and Section 403 (0.91m corridor).
    Returns formatted accessibility context with a fallback dictionary if offline or unauthenticated.
    """
    api_key = (os.getenv("TAVILY_API_KEY") or TAVILY_API_KEY or "").strip()

    # Deterministic fallback dictionary with verified ADA Title III architectural standards
    fallback_dict = AccessibilityDict({
        "status": "OFFLINE_FALLBACK",
        "query": query,
        "source": "ada_title_iii_standards_catalog",
        "standards": {
            "ada_section_404": {
                "section": "ADA Title III Section 404",
                "title": "Doorways, Entrances, and Gates",
                "min_clearance_m": 0.81,
                "min_clearance_inches": 32,
                "requirement": "Clear opening width of doorways shall be 32 inches (815 mm / 0.81m) minimum."
            },
            "ada_section_403": {
                "section": "ADA Title III Section 403",
                "title": "Walking Surfaces & Accessible Routes",
                "min_clearance_m": 0.91,
                "min_clearance_inches": 36,
                "requirement": "Clear width of an interior accessible route shall be 36 inches (915 mm / 0.91m) minimum."
            }
        },
        "ada_doorway_min_clearance_m": 0.81,
        "ada_corridor_min_clearance_m": 0.91,
        "formatted_context": (
            "ADA Title III Section 404: 0.81m (32 in) minimum doorway clearance; "
            "ADA Title III Section 403: 0.91m (36 in) minimum accessible corridor width."
        )
    })

    # If no key or placeholder key, return fallback dictionary
    if not api_key or api_key in ("your_tavily_key_here", "tvly-your_tavily_key_here"):
        return fallback_dict

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, search_depth="basic", max_results=3)

        results = response.get("results", [])
        snippets = [r.get("content", "").strip() for r in results if r.get("content")]
        search_summary = " ".join(snippets[:2]) if snippets else fallback_dict["formatted_context"]

        return AccessibilityDict({
            "status": "SUCCESS",
            "query": query,
            "source": "tavily_search_api",
            "standards": fallback_dict["standards"],
            "ada_doorway_min_clearance_m": 0.81,
            "ada_corridor_min_clearance_m": 0.91,
            "search_summary": search_summary,
            "formatted_context": (
                f"{search_summary} "
                f"[Standards Applied: ADA Section 404 (0.81m doorway), Section 403 (0.91m corridor)]"
            )
        })
    except Exception as e:
        fallback_dict["api_notice"] = f"Tavily API call skipped or offline: {str(e)}"
        return fallback_dict


def get_standard_specs() -> dict:
    """Returns baseline accessibility standards catalog dictionary."""
    return STANDARD_ACCESSIBILITY_CLEARANCES


if __name__ == "__main__":
    print("Testing Tavily Search Integration...")
    context = fetch_accessibility_context("ADA doorway width standards")
    print("Search Result:\n", json.dumps(context, indent=2))