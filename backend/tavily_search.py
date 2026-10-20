import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Standard accessibility clearances catalog
STANDARD_ACCESSIBILITY_CLEARANCES = {
    "doorway": {
        "min_width_meters": 0.81,
        "standard_code": "ADA Title III Section 404.2.3",
        "guideline": "Clear opening width of doorways shall be 32 inches (815 mm) minimum."
    },
    "corridor": {
        "min_width_meters": 0.91,
        "standard_code": "ADA Title III Section 403.5.1",
        "guideline": "Clear width of an interior accessible route shall be 36 inches (915 mm) minimum."
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

def fetch_accessibility_context(query: str = "wheelchair accessibility indoor doorway standards") -> str:
    """
    Fetches real-time spatial and accessibility context using Tavily Search API.
    Falls back gracefully to standard ADA accessibility clearances if the API key
    is not provided or an error occurs.
    """
    api_key = TAVILY_API_KEY or os.getenv("TAVILY_API_KEY", "")
    if not api_key or api_key.strip() in ("", "your_tavily_api_key_here"):
        # Match query keywords against known standards catalog
        q_lower = query.lower()
        if "corridor" in q_lower or "hallway" in q_lower:
            spec = STANDARD_ACCESSIBILITY_CLEARANCES["corridor"]
            return f"Standard: {spec['standard_code']} - {spec['guideline']} (Minimum: {spec['min_width_meters']}m)."
        elif "turn" in q_lower or "radius" in q_lower:
            spec = STANDARD_ACCESSIBILITY_CLEARANCES["turning_radius"]
            return f"Standard: {spec['standard_code']} - {spec['guideline']} (Diameter: {spec['min_diameter_meters']}m)."
        elif "ramp" in q_lower or "slope" in q_lower:
            spec = STANDARD_ACCESSIBILITY_CLEARANCES["ramp_slope"]
            return f"Standard: {spec['standard_code']} - {spec['guideline']} (Max slope: {spec['max_ratio']})."
        else:
            spec = STANDARD_ACCESSIBILITY_CLEARANCES["doorway"]
            return (
                f"Standard: {spec['standard_code']} - {spec['guideline']} "
                f"WAYLO requires a minimum of {spec['min_width_meters']}m clear passage width."
            )

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key.strip())
        response = client.search(query=query, search_depth="basic", max_results=2)
        
        results = response.get("results", [])
        if results:
            content = results[0].get("content", "").strip()
            if content:
                return content
        return "Standard indoor clearance applied: 0.81m doorway, 0.91m corridor (ADA Section 404)."
    except Exception as e:
        print(f"Tavily API call skipped/error: {e}")
        spec = STANDARD_ACCESSIBILITY_CLEARANCES["doorway"]
        return f"Fallback: {spec['standard_code']} ({spec['min_width_meters']}m min clear doorway opening)."

def get_standard_specs() -> dict:
    """Returns the dictionary of baseline accessibility standards."""
    return STANDARD_ACCESSIBILITY_CLEARANCES

if __name__ == "__main__":
    print("Testing Tavily Search Integration...")
    context = fetch_accessibility_context("ADA wheelchair doorway minimum width requirement")
    print("Search Result:", context)