"""
Closed-loop doorway simulation: an unassisted chair versus the same chair with the WAYLO copilot.

User model: the driver holds a heading offset ("drift") with a little hand tremor on top.
Copilot: reads a simulated LiDAR scan, finds the doorway, estimates risk and clearance,
raises its authority alpha smoothly, steers toward the gap centre and brakes with AEB if needed.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

from . import core
from .core import CHAIR_LENGTH_M, CHAIR_WIDTH_M
from .perception import DOOR_Y, WALL_THICKNESS, build_room, detect_gap, front_range, lidar_scan, side_clearances

DT = 0.02
START = (0.0, 0.5)
HEADING_GAIN = 2.5           # first-order heading tracking, 1/s
ALPHA_TAU_S = 0.25           # smoothing of the authority weight (no chattering handover)
LOOKAHEAD_M = 0.35           # aim point beyond the door plane
ASSIST_GAIN = 3.5            # heading-tracking gain of the powered chair when the copilot steers


def footprint_points(x: float, y: float, phi: float, n: int = 10) -> np.ndarray:
    """Sample points around the chair rectangle (centre x, y; heading phi)."""
    hw, hl = CHAIR_WIDTH_M / 2, CHAIR_LENGTH_M / 2
    xs = np.linspace(-hw, hw, n)
    ys = np.linspace(-hl, hl, n)
    pts = [(a, hl) for a in xs] + [(a, -hl) for a in xs] + [(-hw, b) for b in ys] + [(hw, b) for b in ys]
    pts = np.array(pts)
    s, c = math.sin(phi), math.cos(phi)
    wx = x + pts[:, 0] * c + pts[:, 1] * s
    wy = y - pts[:, 0] * s + pts[:, 1] * c
    return np.stack([wx, wy], axis=1)


def collides(room, x, y, phi) -> bool:
    p = footprint_points(x, y, phi)
    for (x0, y0, x1, y1) in room.slabs:
        if np.any((p[:, 0] >= x0) & (p[:, 0] <= x1) & (p[:, 1] >= y0) & (p[:, 1] <= y1)):
            return True
    return False


def door_clearance(room, x, y, phi) -> Optional[float]:
    """Smallest edge-to-jamb gap while any part of the chair is inside the door slab, else None."""
    p = footprint_points(x, y, phi)
    inside = (p[:, 1] >= DOOR_Y - 0.02) & (p[:, 1] <= DOOR_Y + WALL_THICKNESS + 0.02)
    if not np.any(inside):
        return None
    return float(room.door_width / 2 - np.max(np.abs(p[inside, 0])))


def run(assist: bool, drift_deg: float = 14.0, speed_mps: float = 0.85, door_width_m: float = 1.4,
        tremor_deg: float = 2.0, duration_s: float = 9.0, seed: int = 7) -> dict:
    room = build_room(door_width_m)
    rng = np.random.default_rng(seed)
    tremor_phase = rng.uniform(0, 2 * math.pi)
    x, y = START
    phi, alpha, v_prev = 0.0, 0.0, speed_mps
    gap_world = None                       # last detected gap (the door is static in the world)
    rec = {k: [] for k in ["t", "x", "y", "phi_deg", "v", "alpha", "risk", "clear_left", "clear_right",
                           "front_range", "aeb", "gap_width"]}
    collision_t, min_door_clear, x_at_door, stopped = None, None, None, False
    prev_y = y

    for k in range(int(duration_s / DT)):
        t = k * DT
        phi_user = math.radians(drift_deg + tremor_deg * math.sin(2 * math.pi * 4.5 * t + tremor_phase))
        v_user = speed_mps
        risk, clear_l, clear_r, fr, aeb, a_tgt = 0.0, 9.0, 9.0, 9.0, False, 0.0

        if not assist:
            omega = HEADING_GAIN * (phi_user - phi)
            v = v_user
        else:
            scan = lidar_scan(room, x, y, phi)
            fr = front_range(scan)
            clear_l, clear_r = side_clearances(scan)
            gap = detect_gap(scan, y)
            if gap:
                gap_world = gap
            if gap_world is not None:
                dxw, dyw = gap_world["center_x"] - x, gap_world["center_y"] - y
                fwd = dyw * math.cos(phi) + dxw * math.sin(phi)
                lat = dxw * math.cos(phi) - dyw * math.sin(phi)
                slack = gap_world["width"] / 2 - CHAIR_WIDTH_M / 2
                pred_clear = slack - abs(lat)                      # clearance if heading is held
                proximity = core.clamp(1.1 - max(fwd, 0) / 5.0, 0.2, 1.0)
                risk = 100.0 * proximity * core.clamp(abs(lat) / max(slack, 0.05), 0.0, 1.0)
                if fwd > -0.2:                                      # approaching the door plane
                    a_tgt = core.compute_alpha(risk, pred_clear)
                    # centring priority: take the authority needed to remove a visible lateral error
                    if fwd < 3.0:
                        a_tgt = max(a_tgt, min(1.0, abs(lat) / 0.15) * 0.95)
                    phi_cop = phi + math.atan2(lat, max(fwd + LOOKAHEAD_M, 0.3))
                else:                                               # through the door: hand back
                    a_tgt = 0.05
                    phi_cop = phi_user
            else:
                phi_cop = phi_user
            alpha += (a_tgt - alpha) * (DT / ALPHA_TAU_S)
            phi_cmd = core.blend(phi_user, phi_cop, alpha)
            omega = ASSIST_GAIN * (phi_cmd - phi)
            v_cop = min(speed_mps, 0.65) if (gap_world is not None and fr < 3.2) else speed_mps
            v = core.blend(v_user, v_cop, alpha)
            # Autonomous emergency braking from the measured range, independent of alpha
            if core.aeb_required(v, fr - 0.4 if fr < 9 else None):
                aeb, v, omega, alpha = True, 0.0, 0.0, 1.0

        omega = core.clamp(omega, -core.MAX_YAW_RATE, core.MAX_YAW_RATE)
        for key, val in zip(rec.keys(), [t, x, y, math.degrees(phi), v, alpha, risk, clear_l, clear_r, fr, aeb,
                                         gap_world["width"] if gap_world else 0.0]):
            rec[key].append(float(val))

        x_new, y_new, phi_new = x + v * math.sin(phi) * DT, y + v * math.cos(phi) * DT, phi + omega * DT
        dc = door_clearance(room, x_new, y_new, phi_new)
        if dc is not None:
            min_door_clear = dc if min_door_clear is None else min(min_door_clear, dc)
        if collision_t is None and collides(room, x_new, y_new, phi_new):
            collision_t = t
            stopped = True
            break                                           # chair is stopped by the wall
        if prev_y < DOOR_Y <= y_new and x_at_door is None:
            x_at_door = x
        prev_y, x, y, phi = y, x_new, y_new, phi_new
        if y > DOOR_Y + 2.0:
            break

    out = {k: np.array(v) for k, v in rec.items()}
    out["summary"] = {
        "assist": assist,
        "collision": collision_t is not None,
        "collision_time_s": collision_t,
        "passed_door": bool(y > DOOR_Y + WALL_THICKNESS + CHAIR_LENGTH_M / 2) and collision_t is None,
        "min_door_clearance_m": None if min_door_clear is None else round(min_door_clear, 3),
        "lateral_offset_at_door_m": None if x_at_door is None else round(x_at_door, 3),
        "peak_alpha": round(float(out["alpha"].max()), 3) if len(out["alpha"]) else 0.0,
        "aeb_triggered": bool(out["aeb"].any()) if len(out["aeb"]) else False,
        "duration_s": round(float(out["t"][-1]), 2) if len(out["t"]) else 0.0,
    }
    return out


def compare(**kw) -> dict:
    """Run unassisted and assisted simulations with identical driver input."""
    return {"unassisted": run(False, **kw), "waylo": run(True, **kw), "params": kw}
