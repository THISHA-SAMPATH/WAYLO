import os
import re
import json
import math
import requests
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()

DEFAULT_NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1")
DEFAULT_MODEL = os.getenv("NEBIUS_MODEL", "nvidia/Nemotron-3-Ultra-550b-a55b")

def get_api_key(api_key: str | None = None) -> str | None:
    """Retrieves and validates the Nebius API key."""
    key = api_key or os.getenv("NEBIUS_API_KEY")
    if key and key.strip() and key.strip() != "your_nebius_api_key_here":
        return key.strip()
    return None

def compute_shared_autonomy_arbitration(
    hazard_risk: int,
    clearance_left: float,
    clearance_right: float,
    min_safe_clearance: float = 0.35,
    is_emergency: bool = False
) -> float:
    """
    Computes the dynamic arbitration blending factor alpha in [0.0, 1.0].
    alpha = 0.0 -> 100% human joystick control
    alpha = 1.0 -> 100% autonomous copilot trajectory override / emergency stop
    
    Formula blends normalized hazard risk and lateral clearance penetration:
    alpha = clip( 0.6 * (risk / 100) + 0.4 * max(0, (min_safe - min_clearance) / min_safe), 0.0, 1.0 )
    """
    if is_emergency:
        return 1.0

    min_clearance = min(clearance_left, clearance_right)
    risk_factor = min(1.0, max(0.0, hazard_risk / 100.0))
    
    clearance_penalty = 0.0
    if min_clearance < min_safe_clearance:
        clearance_penalty = (min_safe_clearance - max(0.0, min_clearance)) / min_safe_clearance

    raw_alpha = (0.55 * risk_factor) + (0.45 * clearance_penalty)
    # Apply smooth sigmoid-like tapering for subtle adjustments
    alpha = max(0.0, min(1.0, round(raw_alpha, 3)))
    return alpha

def simulate_spatial_inference(
    user_intent: str,
    steering_deg: float,
    speed_mps: float,
    accessibility_context: str | None = None
) -> dict:
    """
    Fallback deterministic spatial copilot simulation when Nebius API key is not configured
    or when running offline. Provides mathematically sound trajectory corrections.
    """
    intent_norm = user_intent.lower()
    
    if "corridor" in intent_norm:
        # Corridor width: 1.2m (-0.6 to +0.6)
        # Wheelchair nominal width ~0.65m.
        # Steering deviation affects left/right clearance
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
        # Docking at table: requires smooth deceleration and centering
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
        # Sudden obstacle directly ahead (e.g., dynamic pedestrian at Y=2.5m)
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
        # Standard Doorway Intent (1.4m opening at Y=4.5m)
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
        "model": "nvidia/Nemotron-3-Ultra-550b-a55b (simulated)",
        "user_intent": user_intent,
        "steering_correction_deg": round(correction, 1),
        "arbitration_alpha": alpha,
        "speed_buffer_override": "EMERGENCY_BRAKE" if emergency_stop else ("ACTIVE" if recommended_vel < speed_mps else "NOMINAL"),
        "recommended_velocity": f"{recommended_vel} m/s",
        "clearance_left": left_clearance,
        "clearance_right": right_clearance,
        "hazard_risk_score": hazard_risk,
        "emergency_stop": emergency_stop,
        "time_to_collision_sec": ttc,
        "spatial_summary": summary
    }
    if accessibility_context:
        res["accessibility_context"] = accessibility_context
    return res


def _extract_json(text: str) -> dict:
    """Parse the model reply; tolerate code fences, <think> blocks and surrounding prose."""
    clean = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\n?", "", clean)
        clean = re.sub(r"\n?```$", "", clean)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def sanitize_inference(parsed: dict, fallback: dict) -> dict:
    """Fill missing fields from the deterministic engine and clamp values to safe ranges."""
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
    num("time_to_collision_sec", 0.0, 60.0)
    num("steering_correction_deg", -45.0, 45.0)
    parsed["emergency_stop"] = bool(parsed.get("emergency_stop", False))
    if parsed["emergency_stop"]:
        parsed["arbitration_alpha"] = 1.0
    return parsed

def analyze_spatial_frame(
    image_payload: str = "mock_frame_data_001",
    user_intent: str = "Align with Doorway",
    steering_deg: float = 0.0,
    speed_mps: float = 0.8,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = DEFAULT_MODEL,
    accessibility_context: str | None = None
) -> dict:
    """
    Sends spatial telemetry and frame metadata to NVIDIA Nemotron / Cosmos on Nebius
    Token Factory to compute dynamic clearance buffers and shared-autonomy trajectory corrections.
    Falls back gracefully to the deterministic simulation engine if API key is not supplied or offline.
    """
    active_key = get_api_key(api_key)
    active_base_url = (base_url or DEFAULT_NEBIUS_BASE_URL).rstrip("/")

    # If no valid API key is available, run simulated spatial engine
    if not active_key:
        return simulate_spatial_inference(user_intent, steering_deg, speed_mps, accessibility_context=accessibility_context)

    headers = {
        "Authorization": f"Bearer {active_key}",
        "Content-Type": "application/json"
    }

    system_prompt = (
        "You are WAYLO, an AI-powered shared-autonomy wheelchair mobility copilot running on "
        "NVIDIA Nemotron / Cosmos on Nebius AI Cloud. "
        "Analyze spatial boundaries, doorway clearance, corridor obstacles, and user steering. "
        "Respond ONLY with a valid JSON object with the following keys:\n"
        "{\n"
        '  "status": "SUCCESS",\n'
        '  "steering_correction_deg": <float adjustment in degrees>,\n'
        '  "speed_buffer_override": "ACTIVE" | "NOMINAL" | "EMERGENCY_BRAKE",\n'
        '  "recommended_velocity": "<float> m/s",\n'
        '  "clearance_left": <float in meters>,\n'
        '  "clearance_right": <float in meters>,\n'
        '  "hazard_risk_score": <int between 0 and 100>,\n'
        '  "emergency_stop": <boolean>,\n'
        '  "arbitration_alpha": <float between 0.0 and 1.0>,\n'
        '  "time_to_collision_sec": <float>,\n'
        '  "spatial_summary": "<clear 1-2 sentence explanation>"\n'
        "}"
    )

    user_prompt = (
        f"User Intent: {user_intent}\n"
        f"Manual Steering Angle: {steering_deg}°\n"
        f"Target Velocity: {speed_mps} m/s\n"
        f"Visual Frame Metadata: {image_payload}"
    )
    if accessibility_context:
        user_prompt += f"\nAccessibility Standards & Context: {accessibility_context}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(
            f"{active_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        parsed = _extract_json(content)
        parsed = sanitize_inference(
            parsed,
            simulate_spatial_inference(user_intent, steering_deg, speed_mps),
        )
        parsed["source"] = "nebius_cloud"
        parsed["model"] = model
        parsed["user_intent"] = user_intent

        # Ensure arbitration_alpha is populated
        if "arbitration_alpha" not in parsed:
            parsed["arbitration_alpha"] = compute_shared_autonomy_arbitration(
                hazard_risk=parsed.get("hazard_risk_score", 20),
                clearance_left=parsed.get("clearance_left", 0.4),
                clearance_right=parsed.get("clearance_right", 0.4),
                is_emergency=parsed.get("emergency_stop", False)
            )

        if accessibility_context:
            parsed["accessibility_context"] = accessibility_context
        return parsed

    except Exception as e:
        # Fall back to simulated inference with error notice in summary
        fallback = simulate_spatial_inference(user_intent, steering_deg, speed_mps, accessibility_context=accessibility_context)
        fallback["source"] = "simulated_copilot_engine (API fallback)"
        fallback["api_notice"] = f"Nebius API call failed: {str(e)}"
        return fallback

if __name__ == "__main__":
    print("Testing WAYLO Nebius Client...")
    res = analyze_spatial_frame(image_payload="test_frame_001", user_intent="Align with Doorway", steering_deg=10.0)
    print("Inference Result:\n", json.dumps(res, indent=2))