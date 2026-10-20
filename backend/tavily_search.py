import os
from dotenv import load_dotenv
from tavily import TavilyClient

# Load environment variables from .env if present
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

def fetch_accessibility_context(query: str = "wheelchair accessibility indoor doorway standards") -> str:
    """
    Fetches real-time spatial and accessibility context using Tavily Search API.
    Falls back gracefully to standard ADA accessibility clearances if the API key
    is not provided or an error occurs.
    """
    api_key = TAVILY_API_KEY or os.getenv("TAVILY_API_KEY", "")
    if not api_key or api_key.strip() in ("", "your_tavily_api_key_here"):
        return (
            "Standard ADA clearance active: Minimum 32 inches (0.81m) clear width for doorways "
            "and 36 inches (0.91m) for accessible routes/corridors."
        )

    try:
        client = TavilyClient(api_key=api_key.strip())
        response = client.search(query=query, search_depth="basic", max_results=2)
        
        results = response.get("results", [])
        if results:
            content = results[0].get("content", "").strip()
            if content:
                return content
        return "Standard indoor clearance applied (1.2m baseline clearance)."
    except Exception as e:
        print(f"Tavily API call skipped/error: {e}")
        return "Fallback: Standard ADA doorway clearance rules active (0.81m min doorway, 0.91m corridor)."

if __name__ == "__main__":
    print("Testing Tavily Search Integration...")
    context = fetch_accessibility_context("ADA wheelchair doorway minimum width requirement")
    print("Search Result:", context)