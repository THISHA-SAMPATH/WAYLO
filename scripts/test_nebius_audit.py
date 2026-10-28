"""
Live Nebius Token Factory Audit Verification Script.

Executes 1 live call for compile_voice_command and 1 live call for narrate_incident.
Prints the returned responses and outputs the full audit log entries with model, latency, and tokens.

Usage:
  python scripts/test_nebius_audit.py [--key YOUR_NEBIUS_API_KEY]
"""

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.nebius_client import (
    compile_voice_command,
    narrate_incident,
    get_nebius_audit_log,
    clear_nebius_audit_log
)


def run_nebius_audit(api_key: str | None = None) -> list:
    clear_nebius_audit_log()
    key = api_key or os.getenv("NEBIUS_API_KEY")
    if key and key.strip() and key.strip() != "your_nebius_api_key_here":
        masked = key[:6] + "..." + key[-4:]
        print(f"[INFO] Using Nebius API Key: {masked}")
    else:
        key = None
        print("[INFO] No live Nebius API key found. Operating in verified fallback audit mode.")

    # 1. compile_voice_command
    print("\n1. Testing compile_voice_command...")
    voice_input = "Please slow down and be cautious through this narrow doorway"
    voice_res = compile_voice_command(voice_input, api_key=key)
    print("Voice Command Compilation Result:")
    print(json.dumps(voice_res, indent=2))

    # 2. narrate_incident
    print("\n2. Testing narrate_incident...")
    incident_event = {
        "event_type": "scrape",
        "door_width_m": 0.81,
        "clearance_m": 0.02,
        "speed_mps": 0.65,
        "human_intent": "Steering forward through doorway",
        "copilot_action": "Applied 0.72 alpha steering correction to maintain centering"
    }
    narration_res = narrate_incident(incident_event, api_key=key)
    print("Incident Caregiver Narration Result:")
    print(json.dumps(narration_res, indent=2))

    # 3. Print audit log entries
    audit_log = get_nebius_audit_log()
    print("\n" + "=" * 80)
    print("  NEBIUS API AUDIT LOG ENTRIES (Recorded in-memory and accessible via API)")
    print("=" * 80)
    print(json.dumps(audit_log, indent=2))
    print("=" * 80 + "\n")
    return audit_log


def main():
    parser = argparse.ArgumentParser(description="Test Nebius live calls and inspect audit log")
    parser.add_argument("--key", type=str, default=None, help="Optional Nebius API key")
    args = parser.parse_args()

    run_nebius_audit(api_key=args.key)


if __name__ == "__main__":
    main()
