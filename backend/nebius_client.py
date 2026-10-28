"""
WAYLO: Nebius AI Studio Client (NVIDIA Nemotron).

Handles non-control reasoning tasks via Nebius Token Factory (NVIDIA Nemotron):
1. compile_voice_command: Compiles natural-language voice instructions into bounded configuration
   parameters (speed_cap_mps in [0.2, 1.0], clearance_margin_m, door_mode), with the deterministic
   safety layer as final authority.
2. narrate_incident: Generates plain-English caregiver summaries from sanitized telemetry events.
3. Audit logging: Logs every call (model, latency, tokens, source) to an audit log exposed by the API.

Hard Constraint Architecture:
The real-time control loop (perception -> alpha blending -> differential command) runs LOCALLY
and NEVER calls the cloud. Clearance and alpha are computed deterministically by local core kinematics.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
from dotenv import load_dotenv

from . import core

load_dotenv()

DEFAULT_NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1")
DEFAULT_MODEL = os.getenv("NEBIUS_MODEL", "nvidia/nemotron-3-ultra")

# In-memory audit trail of Nebius API calls
_NEBIUS_AUDIT_LOG: List[Dict[str, Any]] = []


def get_api_key(api_key: Optional[str] = None) -> Optional[str]:
    """Retrieves and validates the Nebius API key."""
    key = api_key or os.getenv("NEBIUS_API_KEY")
    if key and key.strip() and key.strip() != "your_nebius_api_key_here":
        return key.strip()
    return None


def get_nebius_audit_log() -> List[Dict[str, Any]]:
    """Returns all recorded Nebius API calls."""
    return list(_NEBIUS_AUDIT_LOG)


def clear_nebius_audit_log() -> None:
    """Clears the Nebius API audit log."""
    _NEBIUS_AUDIT_LOG.clear()


def log_nebius_call(
    task: str,
    model: Optional[str],
    latency_ms: float,
    tokens: Dict[str, int],
    source: str,
    status: str = "SUCCESS"
) -> Dict[str, Any]:
    """Appends a call record to the audit log."""
    entry = {
        "timestamp": time.time(),
        "task": task,
        "model": model,
        "latency_ms": round(latency_ms, 2),
        "tokens": {
            "prompt_tokens": tokens.get("prompt_tokens", 0),
            "completion_tokens": tokens.get("completion_tokens", 0),
            "total_tokens": tokens.get("total_tokens", 0)
        },
        "source": source,
        "status": status
    }
    _NEBIUS_AUDIT_LOG.append(entry)
    return entry


def compute_shared_autonomy_arbitration(
    hazard_risk: int,
    clearance_left: float,
    clearance_right: float,
    min_safe_clearance: float = 0.35,
    is_emergency: bool = False
) -> float:
    """
    Local deterministic arbitration blending factor alpha in [0.0, 1.0].
    Executed strictly locally on the wheelchair compute unit.
    """
    if is_emergency:
        return 1.0

    min_clearance = min(clearance_left, clearance_right)
    risk_factor = min(1.0, max(0.0, hazard_risk / 100.0))

    clearance_penalty = 0.0
    if min_clearance < min_safe_clearance:
        clearance_penalty = (min_safe_clearance - max(0.0, min_clearance)) / min_safe_clearance

    raw_alpha = (0.55 * risk_factor) + (0.45 * clearance_penalty)
    return float(core.clamp(round(raw_alpha, 3), 0.0, 1.0))


def _extract_json(text: str) -> dict:
    """Parse JSON reply while stripping thinking tags (<think>...</think>), markdown fences, and prose."""
    clean = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        return json.loads(clean.strip())
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


# ==============================================================================
# Non-Control Task 1: compile_voice_command
# ==============================================================================

def _fallback_compile_voice(text: str) -> Dict[str, Any]:
    """Deterministic offline fallback for voice command compilation. Labeled strictly as fallback."""
    t = text.lower()
    if any(w in t for w in ("slow", "careful", "tight", "crawl", "cautious", "narrow")):
        speed = 0.4
        clearance = 0.25
        mode = "cautious" if "cautious" in t or "careful" in t else "narrow"
    elif any(w in t for w in ("fast", "hurry", "quick", "max", "rush", "speed up")):
        speed = 1.0
        clearance = 0.10
        mode = "standard"
    elif any(w in t for w in ("stop", "halt", "pause", "wait")):
        speed = 0.2
        clearance = 0.35
        mode = "cautious"
    else:
        speed = 0.7
        clearance = 0.15
        mode = "standard"

    return {
        "status": "SUCCESS",
        "speed_cap_mps": speed,
        "clearance_margin_m": clearance,
        "door_mode": mode,
        "intent_summary": f"Deterministic fallback parser: {mode} mode at {speed} m/s",
        "source": "fallback",
        "model": None
    }


def compile_voice_command(
    text: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Translates user spoken voice commands into bounded configuration parameters.
    The deterministic safety layer serves as final authority: clamps strictly enforce
    speed_cap_mps in [0.2, 1.0], clearance_margin_m in [0.05, 0.50], and valid door_mode.
    """
    t0 = time.time()
    active_key = get_api_key(api_key)
    active_base_url = (base_url or DEFAULT_NEBIUS_BASE_URL).rstrip("/")

    if not active_key:
        fallback = _fallback_compile_voice(text)
        log_nebius_call("compile_voice_command", model=None, latency_ms=(time.time() - t0) * 1000,
                        tokens={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        source="fallback")
        return fallback

    system_prompt = (
        "You are the WAYLO Wheelchair Voice Command Compiler running on NVIDIA Nemotron on Nebius Token Factory. "
        "Translate the user's spoken mobility intent into a strictly bounded JSON configuration object.\n"
        "Allowed keys:\n"
        "{\n"
        '  "speed_cap_mps": <float between 0.2 and 1.0>,\n'
        '  "clearance_margin_m": <float between 0.05 and 0.50>,\n'
        '  "door_mode": "standard" | "narrow" | "cautious",\n'
        '  "intent_summary": "<clear 1-sentence description>"\n'
        "}\n"
        "Respond ONLY with valid JSON."
    )

    headers = {
        "Authorization": f"Bearer {active_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User Voice Input: \"{text}\""}
        ],
        "temperature": 0.1
    }

    try:
        resp = requests.post(f"{active_base_url}/chat/completions", headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        resp_data = resp.json()
        latency_ms = (time.time() - t0) * 1000
        content = resp_data["choices"][0]["message"]["content"]
        tokens = resp_data.get("usage", {})

        parsed = _extract_json(content)

        # Deterministic Safety Layer (Final Authority): clamp to hard physical limits
        raw_speed = float(parsed.get("speed_cap_mps", 0.7))
        speed_cap = float(core.clamp(round(raw_speed, 2), 0.2, 1.0))

        raw_margin = float(parsed.get("clearance_margin_m", 0.15))
        clearance_margin = float(core.clamp(round(raw_margin, 2), 0.05, 0.50))

        door_mode = str(parsed.get("door_mode", "standard")).lower().strip()
        if door_mode not in ("standard", "narrow", "cautious"):
            door_mode = "standard"

        log_nebius_call("compile_voice_command", model=model, latency_ms=latency_ms,
                        tokens=tokens, source="nebius_cloud")

        return {
            "status": "SUCCESS",
            "speed_cap_mps": speed_cap,
            "clearance_margin_m": clearance_margin,
            "door_mode": door_mode,
            "intent_summary": parsed.get("intent_summary", f"Command parsed: {text}"),
            "source": "nebius_cloud",
            "model": model or DEFAULT_MODEL,
            "latency_ms": round(latency_ms, 2)
        }

    except Exception as e:
        latency_ms = (time.time() - t0) * 1000
        fallback = _fallback_compile_voice(text)
        fallback["api_notice"] = f"Nebius call failed ({str(e)}), deterministic safety layer applied"
        log_nebius_call("compile_voice_command", model=model, latency_ms=latency_ms,
                        tokens={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        source="fallback", status=f"FAILED: {str(e)}")
        return fallback


# ==============================================================================
# Non-Control Task 2: narrate_incident
# ==============================================================================

def _fallback_narrate_incident(event: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic offline caregiver summary. Labeled strictly as fallback."""
    event_type = str(event.get("event_type", "incident")).lower()
    clearance = event.get("clearance_m", 0.0)
    door_w = event.get("door_width_m", 0.91)
    alpha = event.get("copilot_alpha", 0.0)
    t = event.get("timestamp_s", 0.0)

    if event_type == "near_miss":
        text = (f"At t={t:.1f}s, a near-miss alert occurred ({clearance:.2f}m clearance in a {door_w:.2f}m door). "
                f"WAYLO increased copilot authority (alpha={alpha:.2f}) and safely guided through.")
    elif event_type == "collision":
        text = (f"At t={t:.1f}s, doorway boundary contact was detected. "
                f"Autonomous emergency braking stopped the chair immediately.")
    elif event_type == "scrape":
        text = (f"At t={t:.1f}s, tight doorway passage ({clearance:.2f}m clearance). "
                f"WAYLO smoothly regulated speed and maintained heading.")
    elif event_type == "human_rescue":
        text = (f"At t={t:.1f}s, user regained manual control after assistive intervention.")
    elif event_type == "assist_engaged":
        text = (f"At t={t:.1f}s, WAYLO engaged shared-autonomy copilot (alpha={alpha:.2f}) to align with {door_w:.2f}m doorway.")
    else:
        text = f"Mobility event '{event_type}' logged safely by WAYLO copilot at t={t:.1f}s."

    return {
        "status": "SUCCESS",
        "event_type": event_type,
        "narrative": text,
        "source": "fallback",
        "model": None
    }


def narrate_incident(
    sanitized_event: Dict[str, Any],
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Produces a plain-English caregiver summary for a mobility event.
    Operates ONLY on sanitized event telemetry (no images or raw point clouds).
    """
    t0 = time.time()
    active_key = get_api_key(api_key)
    active_base_url = (base_url or DEFAULT_NEBIUS_BASE_URL).rstrip("/")

    # Sanitize payload: strip any raw array or large structure
    clean_event = {
        k: v for k, v in sanitized_event.items()
        if not isinstance(v, (np.ndarray, list, dict)) or (isinstance(v, list) and len(v) < 10)
    }

    if not active_key:
        fallback = _fallback_narrate_incident(clean_event)
        log_nebius_call("narrate_incident", model=None, latency_ms=(time.time() - t0) * 1000,
                        tokens={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        source="fallback")
        return fallback

    headers = {
        "Authorization": f"Bearer {active_key}",
        "Content-Type": "application/json"
    }

    system_prompt = (
        "You are the WAYLO Mobility Caregiver Assistant running on NVIDIA Nemotron on Nebius Token Factory. "
        "Analyze the provided sanitized wheelchair telemetry event and write a concise, compassionate, "
        "1-2 sentence plain-English summary for a family caregiver or clinician explaining what occurred "
        "and how WAYLO's safety systems responded.\n"
        "Respond ONLY with a valid JSON object in this format:\n"
        "{\n"
        '  "narrative": "<1-2 sentence plain English summary>"\n'
        "}"
    )

    user_prompt = f"Sanitized Telemetry Event: {json.dumps(clean_event)}"

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }

    try:
        resp = requests.post(f"{active_base_url}/chat/completions", headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        resp_data = resp.json()
        latency_ms = (time.time() - t0) * 1000
        content = resp_data["choices"][0]["message"]["content"]
        tokens = resp_data.get("usage", {})

        parsed = _extract_json(content)
        narrative = parsed.get("narrative", "")
        if not narrative:
            narrative = _fallback_narrate_incident(clean_event)["narrative"]

        log_nebius_call("narrate_incident", model=model, latency_ms=latency_ms,
                        tokens=tokens, source="nebius_cloud")

        return {
            "status": "SUCCESS",
            "event_type": clean_event.get("event_type", "event"),
            "narrative": narrative,
            "source": "nebius_cloud",
            "model": model or DEFAULT_MODEL,
            "latency_ms": round(latency_ms, 2)
        }

    except Exception as e:
        latency_ms = (time.time() - t0) * 1000
        fallback = _fallback_narrate_incident(clean_event)
        fallback["api_notice"] = f"Nebius call failed ({str(e)}), offline caregiver fallback provided"
        log_nebius_call("narrate_incident", model=model, latency_ms=latency_ms,
                        tokens={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        source="fallback", status=f"FAILED: {str(e)}")
        return fallback


# ==============================================================================
# Deterministic Spatial Inference & High-Level Assistant
# ==============================================================================

def simulate_spatial_inference(
    user_intent: str = "align_doorway",
    steering_deg: float = 0.0,
    speed_mps: float = 0.8,
    accessibility_context: str | dict | None = None
) -> dict:
    """
    Deterministic spatial copilot simulation. Provides mathematically sound trajectory corrections
    without any cloud dependency.
    """
    intent_norm = user_intent.lower()

    if "corridor" in intent_norm:
        rad = math.radians(steering_deg)
        left_clearance = max(0.08, round(0.40 - (rad * 0.4), 2))
        right_clearance = max(0.08, round(0.40 + (rad * 0.4), 2))
        correction = -steering_deg
        hazard_risk = min(90, max(5, int(abs(steering_deg) * 1.8)))
        emergency_stop = hazard_risk > 75
        recommended_vel = 0.0 if emergency_stop else round(min(speed_mps, 0.6), 2)
        dist_to_hazard = 2.5
        summary = (
            f"Tight Corridor detected (width: 1.2m). Lateral deviation of {steering_deg:+.1f}° "
            f"requires a {correction:+.1f}° shared-autonomy correction to maintain safe wall clearance."
        )

    elif "table" in intent_norm or "dock" in intent_norm:
        left_clearance = round(max(0.15, 0.35 - (steering_deg * 0.005)), 2)
        right_clearance = round(max(0.15, 0.35 + (steering_deg * 0.005)), 2)
        correction = -steering_deg
        hazard_risk = min(80, max(10, int(abs(steering_deg) * 1.2 + (speed_mps * 20))))
        emergency_stop = False
        recommended_vel = round(min(speed_mps, 0.3), 2)
        dist_to_hazard = 1.8
        summary = (
            f"Docking bay at Table identified at Y=3.5m. Regulating approach speed to "
            f"{recommended_vel} m/s and applying {correction:+.1f}° centering vector."
        )

    elif "emergency" in intent_norm or "stop" in intent_norm:
        left_clearance = 0.12
        right_clearance = 0.14
        correction = 0.0
        hazard_risk = 96
        emergency_stop = True
        recommended_vel = 0.0
        dist_to_hazard = 0.45
        summary = (
            "CRITICAL: Dynamic hazard detected 0.45m ahead directly in trajectory path. "
            "Autonomous emergency braking (AEB) triggered. Wheelchair halted."
        )

    else:
        # Standard Doorway Intent
        if steering_deg == 0.0:
            left_clearance = 0.42
            right_clearance = 0.38
            correction = 8.5
            hazard_risk = 12
            emergency_stop = False
            recommended_vel = 0.7
            dist_to_hazard = 3.5
            summary = (
                "Doorway detected. Target clear opening aligned with 8.5° steering correction "
                "(0.42m left, 0.38m right clearance). Safe clearance maintained."
            )
        else:
            left_clearance = round(max(0.10, 0.42 - (steering_deg * 0.008)), 2)
            right_clearance = round(max(0.10, 0.38 + (steering_deg * 0.008)), 2)
            correction = -steering_deg
            hazard_risk = min(85, max(8, int(abs(steering_deg) * 1.4)))
            emergency_stop = hazard_risk > 70
            recommended_vel = 0.0 if emergency_stop else round(min(speed_mps, 0.7), 2)
            dist_to_hazard = 3.5
            summary = (
                f"Doorway detected at Y=4.5m (1.4m opening). Compensating user steering "
                f"by {correction:+.1f}° to center trajectory through gateway."
            )

    alpha = compute_shared_autonomy_arbitration(
        hazard_risk=hazard_risk,
        clearance_left=left_clearance,
        clearance_right=right_clearance,
        is_emergency=emergency_stop
    )

    ttc = round(dist_to_hazard / max(0.05, speed_mps), 2) if not emergency_stop else 0.0

    res = {
        "status": "SUCCESS",
        "source": "simulated_copilot_engine",
        "model": "deterministic_safety_layer",
        "user_intent": user_intent,
        "clearance_left_m": left_clearance,
        "clearance_right_m": right_clearance,
        "clearance_left": left_clearance,
        "clearance_right": right_clearance,
        "steering_correction_deg": round(correction, 1),
        "emergency_stop": emergency_stop,
        "spatial_summary": summary,
        "arbitration_alpha": alpha,
        "speed_buffer_override": "EMERGENCY_BRAKE" if emergency_stop else ("ACTIVE" if recommended_vel < speed_mps else "NOMINAL"),
        "recommended_velocity": f"{recommended_vel} m/s",
        "hazard_risk_score": hazard_risk,
        "time_to_collision_sec": ttc,
    }
    if accessibility_context:
        res["accessibility_context"] = str(accessibility_context)
    return res


def sanitize_inference(parsed: dict, fallback: dict) -> dict:
    """Fill missing fields from deterministic engine and clamp values to safe physical ranges."""
    for key, value in fallback.items():
        parsed.setdefault(key, value)

    def num(key, lo, hi, cast=float):
        try:
            parsed[key] = cast(min(hi, max(lo, float(parsed[key]))))
        except (TypeError, ValueError):
            parsed[key] = fallback[key]

    num("arbitration_alpha", 0.0, 1.0)
    num("hazard_risk_score", 0, 100, int)
    num("clearance_left", 0.0, 5.0)
    num("clearance_right", 0.0, 5.0)
    if "clearance_left_m" in parsed:
        num("clearance_left_m", 0.0, 5.0)
    if "clearance_right_m" in parsed:
        num("clearance_right_m", 0.0, 5.0)
    num("time_to_collision_sec", 0.0, 60.0)
    num("steering_correction_deg", -45.0, 45.0)
    parsed["emergency_stop"] = bool(parsed.get("emergency_stop", False))
    if parsed["emergency_stop"]:
        parsed["arbitration_alpha"] = 1.0
    return parsed


def analyze_spatial_frame(
    image_payload: str = "",
    user_intent: str = "align_doorway",
    steering_deg: float = 0.0,
    speed_mps: float = 0.8,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    accessibility_context: Optional[Any] = None,
    **kwargs
) -> dict:
    """
    Deterministic spatial inference wrapper.
    Ensures clearance and arbitration alpha values are ALWAYS determined by the local
    deterministic safety layer, never by LLM hallucinations.
    """
    t0 = time.time()
    fallback = simulate_spatial_inference(
        user_intent=user_intent,
        steering_deg=steering_deg,
        speed_mps=speed_mps,
        accessibility_context=accessibility_context
    )

    active_key = get_api_key(api_key)
    if not active_key:
        return fallback

    active_base_url = (base_url or DEFAULT_NEBIUS_BASE_URL).rstrip("/")
    headers = {"Authorization": f"Bearer {active_key}", "Content-Type": "application/json"}
    system_prompt = (
        "You are WAYLO High-Level Spatial Mobility Assistant on NVIDIA Nemotron on Nebius Token Factory. "
        "Provide a high-level situational summary for the user intent. "
        "Respond ONLY with valid JSON: {\"spatial_summary\": \"<clear 1-2 sentence description>\"}"
    )
    user_prompt = f"User Intent: {user_intent}, Steering: {steering_deg} deg, Speed: {speed_mps} m/s."
    if image_payload:
        user_prompt += f", Scene: {image_payload}"

    try:
        resp = requests.post(
            f"{active_base_url}/chat/completions",
            headers=headers,
            json={
                "model": model or DEFAULT_MODEL,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "temperature": 0.1
            },
            timeout=15
        )
        resp.raise_for_status()
        latency_ms = (time.time() - t0) * 1000
        content = resp.json()["choices"][0]["message"]["content"]
        tokens = resp.json().get("usage", {})
        parsed = _extract_json(content)

        # Merge summary but preserve deterministic clearances and alpha
        fallback["spatial_summary"] = parsed.get("spatial_summary", fallback["spatial_summary"])
        fallback["source"] = "nebius_cloud"
        fallback["model"] = model or DEFAULT_MODEL
        log_nebius_call("spatial_summary", model=model, latency_ms=latency_ms, tokens=tokens, source="nebius_cloud")
        return fallback

    except Exception as e:
        fallback["source"] = "simulated_copilot_engine (API fallback)"
        fallback["api_notice"] = f"Nebius API call failed: {str(e)}"
        return fallback


if __name__ == "__main__":
    print("Testing Nebius Client Non-Control Functions...")
    v = compile_voice_command("Slow down and carefully approach the narrow bathroom door")
    print("Voice Command Compilation:\n", json.dumps(v, indent=2))

    n = narrate_incident({
        "event_type": "near_miss",
        "timestamp_s": 2.4,
        "door_width_m": 0.81,
        "clearance_m": 0.06,
        "copilot_alpha": 0.82
    })
    print("Incident Narration:\n", json.dumps(n, indent=2))
    print("Audit Log:\n", json.dumps(get_nebius_audit_log(), indent=2))