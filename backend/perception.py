"""
Simulated 2D LiDAR and gap perception.

The chair carries a forward-facing 180-degree range scanner. Ranges are produced by ray-casting
against the room geometry, and the doorway is *detected from the scan* (not read from the
scenario definition): the controller only sees ranges, like it would with real hardware.

World frame: x to the right, y forward. Heading phi is measured clockwise from +y, so a point
straight ahead of a chair at heading phi lies in direction (sin phi, cos phi).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .core import CHAIR_WIDTH_M

ROOM_HALF_WIDTH = 4.0
ROOM_DEPTH = 8.0
DOOR_Y = 4.5
WALL_THICKNESS = 0.15


@dataclass
class Room:
    door_width: float
    segments: np.ndarray      # (K, 4) x1, y1, x2, y2 used for ray casting
    slabs: list               # door-wall rectangles (xmin, ymin, xmax, ymax) used for collision tests


def build_room(door_width: float = 1.4) -> Room:
    w2 = door_width / 2.0
    H, D, Y, T = ROOM_HALF_WIDTH, ROOM_DEPTH, DOOR_Y, WALL_THICKNESS
    segs = [
        (-H, 0, -H, D), (H, 0, H, D), (-H, D, H, D), (-H, 0, H, 0),            # outer walls
        (-H, Y, -w2, Y), (w2, Y, H, Y),                                       # door wall, front face
        (-H, Y + T, -w2, Y + T), (w2, Y + T, H, Y + T),                       # door wall, back face
        (-w2, Y, -w2, Y + T), (w2, Y, w2, Y + T),                             # jamb edges
    ]
    slabs = [(-H, Y, -w2, Y + T), (w2, Y, H, Y + T)]
    return Room(door_width, np.array(segs, dtype=float), slabs)


def lidar_scan(room: Room, x: float, y: float, phi: float, n_rays: int = 61,
               fov_deg: float = 180.0, max_range: float = 7.0, sensor_offset: float = 0.40) -> dict:
    """Ray-cast a forward scanner. Returns relative angles, ranges and world hit points."""
    rel = np.radians(np.linspace(-fov_deg / 2, fov_deg / 2, n_rays))
    ox, oy = x + sensor_offset * math.sin(phi), y + sensor_offset * math.cos(phi)
    dx, dy = np.sin(phi + rel), np.cos(phi + rel)                    # (n,)

    s = room.segments
    p1x, p1y = s[:, 0][None, :], s[:, 1][None, :]                    # (1, K)
    ex, ey = (s[:, 2] - s[:, 0])[None, :], (s[:, 3] - s[:, 1])[None, :]
    dxx, dyy = dx[:, None], dy[:, None]                              # (n, 1)

    denom = dxx * ey - dyy * ex
    with np.errstate(divide="ignore", invalid="ignore"):
        t = ((p1x - ox) * ey - (p1y - oy) * ex) / denom
        u = ((p1x - ox) * dyy - (p1y - oy) * dxx) / denom
    valid = (np.abs(denom) > 1e-9) & (t > 1e-6) & (u >= 0.0) & (u <= 1.0)
    t = np.where(valid, t, np.inf)
    ranges = np.minimum(t.min(axis=1), max_range)
    hits = np.stack([ox + dx * ranges, oy + dy * ranges], axis=1)
    return {"rel_angles": rel, "ranges": ranges, "hits": hits, "origin": (ox, oy), "max_range": max_range}


def detect_gap(scan: dict, pose_y: float) -> Optional[dict]:
    """
    Find the doorway opening in a scan. The nearest forward wall plane is taken as the
    door wall; rays that pass through it form the gap; the wall hits on either side give its edges.
    Returns world-frame gap centre and width, or None if no gap is visible.
    """
    rel, r, hits = scan["rel_angles"], scan["ranges"], scan["hits"]
    fan = np.abs(rel) <= math.radians(60)
    idx = np.where(fan)[0]
    hy, hx = hits[idx, 1], hits[idx, 0]
    ahead = hy > pose_y + 0.3
    if not np.any(ahead):
        return None
    # The door wall is the nearest *horizontal* surface: many hits sharing (almost) the same y.
    # Side walls are vertical, so their hits are spread over many y values and are rejected.
    ys = np.sort(hy[ahead])
    wall_y, start = None, 0
    for i in range(1, len(ys) + 1):
        if i == len(ys) or ys[i] - ys[i - 1] > 0.08:
            if i - start >= 4:
                wall_y = float(np.mean(ys[start:i]))
                break
            start = i
    if wall_y is None:
        return None
    is_wall = np.abs(hy - wall_y) < 0.12
    at_max = r[idx] >= scan["max_range"] - 1e-6
    through = ((hy > wall_y + 0.6) | at_max) & ~is_wall
    if not np.any(through) or not np.any(is_wall):
        return None
    # longest contiguous run of through-rays
    best, cur = (0, -1), None
    for i, flag in enumerate(through):
        if flag and cur is None:
            cur = i
        if (not flag or i == len(through) - 1) and cur is not None:
            end = i if flag else i - 1
            if end - cur > best[1] - best[0]:
                best = (cur, end)
            cur = None
    a, b = best
    if b < a:
        return None
    left_wall = [i for i in range(a) if is_wall[i]]
    right_wall = [i for i in range(b + 1, len(is_wall)) if is_wall[i]]
    if not left_wall or not right_wall:
        return None
    xl = hx[left_wall[-1]]       # nearest wall hit left of the gap
    xr = hx[right_wall[0]]       # nearest wall hit right of the gap
    return {"center_x": float((xl + xr) / 2), "center_y": float(wall_y),
            "width": float(abs(xr - xl)), "left_edge_x": float(xl), "right_edge_x": float(xr)}


def front_range(scan: dict, half_angle_deg: float = 6.0) -> float:
    m = np.abs(scan["rel_angles"]) <= math.radians(half_angle_deg)
    return float(np.min(scan["ranges"][m]))


def side_clearances(scan: dict) -> tuple[float, float]:
    """Edge-to-wall clearance on the left and right, from the two outermost rays."""
    r = scan["ranges"]
    return max(0.0, float(r[0]) - CHAIR_WIDTH_M / 2), max(0.0, float(r[-1]) - CHAIR_WIDTH_M / 2)


def scan_summary_text(scan: dict, gap: Optional[dict]) -> str:
    """Compact natural-language description of the scan, suitable for the Nemotron prompt."""
    fr = front_range(scan)
    left, right = side_clearances(scan)
    txt = f"2D LiDAR (61 rays, 180 deg): nearest obstacle ahead {fr:.2f} m; side clearance left {left:.2f} m, right {right:.2f} m."
    if gap:
        txt += (f" Opening detected {gap['center_y'] - scan['origin'][1]:.2f} m ahead, "
                f"{gap['width']:.2f} m wide, centred {gap['center_x'] - scan['origin'][0]:+.2f} m laterally.")
    else:
        txt += " No opening detected in the forward field of view."
    return txt
