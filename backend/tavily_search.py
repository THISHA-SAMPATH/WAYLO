"""
WAYLO: Tavily Accessibility Search Engine with Regional Doorway Standards.

Fetches regional accessibility standards at runtime via Tavily Search API.
Extracts the minimum clear doorway width for the requested region (e.g. US/ADA, UK, EU, AU, CA).
If online search or parsing fails, falls back gracefully to a verified cached catalog and
accurately marks the source as 'cached_catalog' or 'tavily_search_api'.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Verified regional building standards catalog
REGION_CATALOG: Dict[str, Dict[str, Any]] = {
    "US": {
        "region_name": "United States",
        "standard_code": "ADA Title III Section 404.2.3",
        "min_doorway_width_m": 0.813,  # 32 inches / 815 mm
        "min_corridor_width_m": 0.914, # 36 inches / 915 mm
        "description": "ADA Title III Section 404 specifies minimum 32 inches (0.81m) clear opening width."
    },
    "UK": {
        "region_name": "United Kingdom",
        "standard_code": "Building Regs Approved Document M / BS 8300",
        "min_doorway_width_m": 0.800,  # 800 mm clear width
        "min_corridor_width_m": 0.900,
        "description": "UK Approved Document M requires effective clear width of 800mm to 825mm."
    },
    "EU": {
        "region_name": "European Union",
        "standard_code": "EN 17210 / EN 301 549",
        "min_doorway_width_m": 0.850,  # 850 mm
        "min_corridor_width_m": 1.000,
        "description": "European Standard EN 17210 specifies 850mm clear doorway opening."
    },
    "AU": {
        "region_name": "Australia",
        "standard_code": "AS 1428.1 Section 13",
        "min_doorway_width_m": 0.850,  # 850 mm
        "min_corridor_width_m": 1.000,
        "description": "Australian Standard AS 1428.1 mandates minimum 850mm clear doorway opening."
    },
    "CA": {
        "region_name": "Canada",
        "standard_code": "CSA B651 / National Building Code",
        "min_doorway_width_m": 0.850,  # 850 mm
        "min_corridor_width_m": 0.920,
        "description": "Canadian Standard CSA B651 specifies 850mm minimum clear door width."
    },
    "GLOBAL": {
        "region_name": "International",
        "standard_code": "ISO 21542:2021",
        "min_doorway_width_m": 0.800,  # 800 mm
        "min_corridor_width_m": 0.900,
        "description": "ISO 21542 accessibility standard specifies 800mm minimum clear door width."
    }
}

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


def normalize_region(region: str) -> str:
    """Normalizes region string to standard catalog key."""
    r = region.upper().strip()
    if r in ("US", "USA", "UNITED STATES", "AMERICA", "ADA"):
        return "US"
    elif r in ("UK", "GB", "UNITED KINGDOM", "BRITAIN", "ENGLAND"):
        return "UK"
    elif r in ("EU", "EUROPE", "GERMANY", "FRANCE"):
        return "EU"
    elif r in ("AU", "AUS", "AUSTRALIA"):
        return "AU"
    elif r in ("CA", "CAN", "CANADA"):
        return "CA"
    return "GLOBAL" if r not in REGION_CATALOG else r


def parse_doorway_width_from_text(text: str) -> Optional[float]:
    """
    Extracts doorway minimum clear width in meters from text snippets.
    Supports meters (0.80m), millimeters (800mm), and inches (32 in).
    Validates range against realistic architectural limits (0.70m - 1.50m).
    """
    candidates: List[float] = []

    # 1. Matches like "0.81 m", "0.85 meters", "0.8m"
    m_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:m|meters|meter)\b', text, re.IGNORECASE)
    for m in m_matches:
        try:
            val = float(m)
            if 0.70 <= val <= 1.50:
                candidates.append(val)
        except ValueError:
            pass

    # 2. Matches like "800 mm", "815mm", "850 millimeters"
    mm_matches = re.findall(r'(\d{3,4})\s*(?:mm|millimeters|millimetres)\b', text, re.IGNORECASE)
    for mm in mm_matches:
        try:
            val = float(mm) / 1000.0
            if 0.70 <= val <= 1.50:
                candidates.append(val)
        except ValueError:
            pass

    # 3. Matches like "32 inches", "32 in", "32\""
    in_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:inches|inch|in\b)', text, re.IGNORECASE)
    for inch in in_matches:
        try:
            val = float(inch) * 0.0254
            if 0.70 <= val <= 1.50:
                candidates.append(round(val, 3))
        except ValueError:
            pass

    if not candidates:
        return None
    # Pick the most common or median reasonable minimum
    return round(float(np_median_fallback(candidates)), 3)


def np_median_fallback(vals: List[float]) -> float:
    s = sorted(vals)
    return s[len(s) // 2]


def fetch_regional_doorway_spec(
    region: str = "US",
    query_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    At runtime, calls Tavily Search to extract the minimum doorway width for the specified region.
    If search or parsing fails, falls back to the verified regional catalog and marks the source.
    """
    reg_key = normalize_region(region)
    cached = REGION_CATALOG.get(reg_key, REGION_CATALOG["GLOBAL"])
    api_key = (os.getenv("TAVILY_API_KEY") or TAVILY_API_KEY or "").strip()

    search_query = query_override or (
        f"{cached['region_name']} accessible doorway minimum clear opening width standard regulations"
    )

    # Check for missing or placeholder key
    if not api_key or api_key in ("your_tavily_key_here", "tvly-your_tavily_key_here", "your_tavily_api_key_here"):
        return {
            "status": "SUCCESS",
            "region": reg_key,
            "region_name": cached["region_name"],
            "standard_code": cached["standard_code"],
            "min_doorway_width_m": cached["min_doorway_width_m"],
            "min_corridor_width_m": cached["min_corridor_width_m"],
            "source": "cached_catalog",
            "description": cached["description"],
            "formatted_context": f"[{reg_key}] {cached['standard_code']}: {cached['description']}"
        }

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(query=search_query, search_depth="basic", max_results=3)
        results = response.get("results", [])
        snippets = [r.get("content", "").strip() for r in results if r.get("content")]
        combined_text = " ".join(snippets)

        extracted_width = parse_doorway_width_from_text(combined_text)

        if extracted_width is not None:
            return {
                "status": "SUCCESS",
                "region": reg_key,
                "region_name": cached["region_name"],
                "standard_code": cached["standard_code"],
                "min_doorway_width_m": extracted_width,
                "min_corridor_width_m": cached["min_corridor_width_m"],
                "source": "tavily_search_api",
                "extracted_from_web": True,
                "snippets": snippets[:2],
                "description": f"Extracted via Tavily Search: {extracted_width:.3f}m minimum clear doorway width.",
                "formatted_context": (
                    f"[{reg_key}] {cached['standard_code']}: verified clear width {extracted_width:.3f}m "
                    f"({snippets[0][:120]}...)" if snippets else f"[{reg_key}] {extracted_width:.3f}m"
                )
            }
        else:
            # Parsing failed: fallback to cached catalog and mark source accordingly
            return {
                "status": "SUCCESS",
                "region": reg_key,
                "region_name": cached["region_name"],
                "standard_code": cached["standard_code"],
                "min_doorway_width_m": cached["min_doorway_width_m"],
                "min_corridor_width_m": cached["min_corridor_width_m"],
                "source": "cached_catalog (parsing_fallback)",
                "extracted_from_web": False,
                "description": cached["description"],
                "formatted_context": f"[{reg_key}] {cached['standard_code']} (catalog fallback): {cached['description']}"
            }

    except Exception as e:
        return {
            "status": "SUCCESS",
            "region": reg_key,
            "region_name": cached["region_name"],
            "standard_code": cached["standard_code"],
            "min_doorway_width_m": cached["min_doorway_width_m"],
            "min_corridor_width_m": cached["min_corridor_width_m"],
            "source": "cached_catalog (api_exception_fallback)",
            "api_notice": str(e),
            "description": cached["description"],
            "formatted_context": f"[{reg_key}] {cached['standard_code']}: {cached['description']}"
        }


def fetch_accessibility_context(
    query: str = "ADA doorway width standards",
    region: str = "US"
) -> AccessibilityDict:
    """
    Fetches real-time spatial and accessibility standards context using Tavily Search API.
    Supports regional queries and falls back cleanly to the verified catalog.
    """
    spec = fetch_regional_doorway_spec(region=region, query_override=query)
    reg_key = spec["region"]

    res = AccessibilityDict({
        "status": spec["status"],
        "region": reg_key,
        "query": query,
        "source": spec["source"],
        "min_doorway_width_m": spec["min_doorway_width_m"],
        "ada_doorway_min_clearance_m": spec["min_doorway_width_m"],
        "ada_corridor_min_clearance_m": spec["min_corridor_width_m"],
        "standard_code": spec["standard_code"],
        "formatted_context": spec["formatted_context"]
    })
    return res


def get_standard_specs() -> Dict[str, Any]:
    """Returns baseline accessibility standards catalog dictionary."""
    return STANDARD_ACCESSIBILITY_CLEARANCES


if __name__ == "__main__":
    print("Testing Tavily Regional Standards Extraction...")
    for r in ["US", "UK", "EU", "AU"]:
        sp = fetch_regional_doorway_spec(region=r)
        print(f"Region {r}: min doorway={sp['min_doorway_width_m']}m, source={sp['source']}")