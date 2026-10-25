"""
WAYLO core: single source of truth for constants, shared-autonomy arbitration and
differential-drive kinematics. Used by the API, the closed-loop simulator and the tests.
"""
from __future__ import annotations

import math

# --- Physical constants (metres, seconds) ---
WHEELBASE_M = 0.60          # track width between drive wheels
WHEEL_RADIUS_M = 0.16
CHAIR_WIDTH_M = 0.65
CHAIR_LENGTH_M = 0.95
MAX_DECEL_MPS2 = 2.0
REACTION_TIME_S = 0.15      # sensing + actuation latency used in the braking model
BRAKE_MARGIN_M = 0.10
SAFE_CLEARANCE_M = 0.35     # side clearance below which the copilot starts taking authority
MAX_YAW_RATE = 1.5          # rad/s, passenger comfort limit


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def stopping_distance(v: float, a_max: float = MAX_DECEL_MPS2,
                      reaction_s: float = REACTION_TIME_S, margin: float = BRAKE_MARGIN_M) -> float:
    """Distance needed to stop: reaction travel + v^2 / (2 a) + safety margin."""
    v = max(0.0, v)
    return v * reaction_s + (v * v) / (2.0 * max(0.5, a_max)) + margin


def aeb_required(v: float, obstacle_distance_m: float | None, **kw) -> bool:
    """Autonomous emergency braking trigger, driven by a measured distance (not by a label)."""
    if obstacle_distance_m is None:
        return False
    return obstacle_distance_m <= stopping_distance(v, **kw)


def compute_alpha(hazard_risk: float, min_clearance: float, is_emergency: bool = False) -> float:
    """
    Authority weight alpha in [0, 1].
        alpha = 0.55 * risk/100 + 0.45 * max(0, (0.35 - min_clearance) / 0.35)
    Emergency forces alpha = 1.
    """
    if is_emergency:
        return 1.0
    deficit = max(0.0, (SAFE_CLEARANCE_M - min_clearance) / SAFE_CLEARANCE_M)
    return clamp(0.55 * (clamp(hazard_risk, 0, 100) / 100.0) + 0.45 * deficit, 0.0, 1.0)


def blend(user: float, copilot: float, alpha: float) -> float:
    """Linear shared-autonomy blend: (1 - alpha) * user + alpha * copilot."""
    return (1.0 - alpha) * user + alpha * copilot


def wheel_speeds(v: float, omega: float, wheelbase: float = WHEELBASE_M,
                 wheel_radius: float = WHEEL_RADIUS_M) -> dict:
    """Differential-drive kinematics: body (v, omega) -> wheel linear and angular speeds."""
    v_r = v + omega * wheelbase / 2.0
    v_l = v - omega * wheelbase / 2.0
    return {"left_mps": v_l, "right_mps": v_r,
            "left_rad_s": v_l / wheel_radius, "right_rad_s": v_r / wheel_radius}


def wrap_angle(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi
