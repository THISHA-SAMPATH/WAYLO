"""Closed-loop doorway run: unassisted chair vs WAYLO, with a time scrubber and live LiDAR view."""
import math
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from matplotlib.patches import Polygon, Rectangle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend import simulation as sim  # noqa: E402
from backend.core import CHAIR_LENGTH_M, CHAIR_WIDTH_M  # noqa: E402
from backend.perception import DOOR_Y, WALL_THICKNESS, build_room, lidar_scan  # noqa: E402

BG, PANEL, GRID = "#0b0f19", "#111827", "#1f2937"
RED, GREEN, CYAN, MUTED = "#f43f5e", "#22c55e", "#38bdf8", "#94a3b8"


@st.cache_data(show_spinner=False)
def _run(drift, speed, door, tremor):
    return sim.compare(drift_deg=drift, speed_mps=speed, door_width_m=door, tremor_deg=tremor)


def _chair(ax, x, y, phi, color, alpha=0.35):
    hw, hl = CHAIR_WIDTH_M / 2, CHAIR_LENGTH_M / 2
    corners = np.array([(-hw, -hl), (hw, -hl), (hw, hl), (-hw, hl)])
    s, c = math.sin(phi), math.cos(phi)
    pts = np.stack([x + corners[:, 0] * c + corners[:, 1] * s, y - corners[:, 0] * s + corners[:, 1] * c], axis=1)
    ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor=color, alpha=alpha, lw=1.4, zorder=4))
    ax.plot([x, x + 0.45 * s], [y, y + 0.45 * c], color=color, lw=2, zorder=5)


def _index(run, t):
    return int(np.clip(np.searchsorted(run["t"], t), 0, len(run["t"]) - 1))


def _scene(res, door, t):
    fig, ax = plt.subplots(figsize=(6.2, 6.2), facecolor=BG)
    ax.set_facecolor(PANEL)
    room = build_room(door)
    w2 = door / 2
    for (x0, y0, x1, y1) in room.slabs:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="#475569", zorder=2))
    ax.plot([-w2, w2], [DOOR_Y + WALL_THICKNESS / 2] * 2, ls=(0, (4, 3)), color=GREEN, lw=1.2, alpha=0.7, zorder=3)
    ax.text(0, DOOR_Y + 0.35, f"door {door:.2f} m", color=MUTED, ha="center", fontsize=8)

    i_w = _index(res["waylo"], t)
    w = res["waylo"]
    scan = lidar_scan(room, w["x"][i_w], w["y"][i_w], math.radians(w["phi_deg"][i_w]))
    ox, oy = scan["origin"]
    for hx, hy in scan["hits"][::2]:
        ax.plot([ox, hx], [oy, hy], color=CYAN, lw=0.5, alpha=0.28, zorder=1)

    for name, color in (("unassisted", RED), ("waylo", GREEN)):
        r = res[name]
        i = _index(r, t)
        ax.plot(r["x"][: i + 1], r["y"][: i + 1], color=color, lw=2.4, zorder=6,
                label="No assist" if name == "unassisted" else "WAYLO")
        _chair(ax, r["x"][i], r["y"][i], math.radians(r["phi_deg"][i]), color)

    u = res["unassisted"]["summary"]
    if u["collision"] and t >= (u["collision_time_s"] or 0):
        i = _index(res["unassisted"], t)
        ax.plot(res["unassisted"]["x"][i], res["unassisted"]["y"][i] + 0.55, marker="X", color="#fbbf24", ms=14, zorder=8)

    ax.set_xlim(-2.6, 2.6)
    ax.set_ylim(0, 7.2)
    ax.set_aspect("equal")
    ax.set_xlabel("lateral x (m)", color=MUTED)
    ax.set_ylabel("forward y (m)", color=MUTED)
    ax.grid(color=GRID, lw=0.5)
    ax.tick_params(colors=MUTED, labelsize=8)
    for sp in ax.spines.values():
        sp.set_color(GRID)
    ax.legend(loc="lower right", facecolor=PANEL, edgecolor=GRID, labelcolor="#e2e8f0", fontsize=8)
    fig.tight_layout()
    return fig


def _timeline(res, t):
    w = res["waylo"]
    fig, ax = plt.subplots(figsize=(6.2, 3.0), facecolor=BG)
    ax.set_facecolor(PANEL)
    ax.plot(w["t"], w["alpha"], color=GREEN, lw=2.2, label="authority α")
    ax.plot(w["t"], np.clip(w["risk"] / 100, 0, 1), color="#fbbf24", lw=1.6, label="hazard risk")
    ax.plot(w["t"], np.clip(np.abs(w["phi_deg"]) / 45, 0, 1), color=CYAN, lw=1.4, ls="--", label="|heading| / 45°")
    ax.axvline(t, color="#e2e8f0", lw=1, alpha=0.7)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("time (s)", color=MUTED)
    ax.grid(color=GRID, lw=0.5)
    ax.tick_params(colors=MUTED, labelsize=8)
    for sp in ax.spines.values():
        sp.set_color(GRID)
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor="#e2e8f0", fontsize=8, ncol=3, loc="upper right")
    fig.tight_layout()
    return fig


def render_closed_loop(default_drift: float = 14.0, default_speed: float = 0.85):
    st.subheader("🚪 Closed-Loop Doorway Run")
    st.caption("Same driver input, run twice through a simulated LiDAR room. The copilot sees only ranges: "
               "it finds the doorway in the scan, raises its authority α, and brakes from measured distance.")

    c1, c2 = st.columns(2)
    door = c1.slider("Door opening (m)  ·  ADA minimum is 0.815", 0.85, 1.60, 1.40, 0.05, key="cl_door")
    tremor = c2.slider("Hand tremor amplitude (°)", 0.0, 6.0, 2.0, 0.5, key="cl_tremor")

    res = _run(float(default_drift), float(default_speed), float(door), float(tremor))
    u, w = res["unassisted"]["summary"], res["waylo"]["summary"]
    t_end = float(max(res["unassisted"]["t"][-1], res["waylo"]["t"][-1]))
    t_default = float(u["collision_time_s"]) if u["collision"] else min(4.0, t_end)
    t = st.slider("Scrub time (s)", 0.0, round(t_end, 2), round(min(t_default, t_end), 2), 0.05, key="cl_time")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("No assist", "💥 Collision" if u["collision"] else "✅ Passed",
              f"clearance {u['min_door_clearance_m']:+.2f} m" if u["min_door_clearance_m"] is not None else None,
              delta_color="off")
    m2.metric("WAYLO", "💥 Collision" if w["collision"] else ("✅ Passed" if w["passed_door"] else "🛑 Stopped safely"),
              f"clearance {w['min_door_clearance_m']:+.2f} m" if w["min_door_clearance_m"] is not None else None,
              delta_color="off")
    m3.metric("Peak authority α", f"{w['peak_alpha']:.2f}")
    m4.metric("Offset at door", f"{w['lateral_offset_at_door_m']:+.2f} m" if w["lateral_offset_at_door_m"] is not None else "n/a")

    left, right = st.columns([1.05, 1])
    with left:
        fig = _scene(res, door, t)
        st.pyplot(fig)
        plt.close(fig)
    with right:
        fig = _timeline(res, t)
        st.pyplot(fig)
        plt.close(fig)
        i = _index(res["waylo"], t)
        wv = res["waylo"]
        st.markdown(
            f"**t = {t:.2f} s** · α **{wv['alpha'][i]:.2f}** · speed **{wv['v'][i]:.2f} m/s** · "
            f"range ahead **{min(wv['front_range'][i], 9):.2f} m**"
            + (" · 🛑 **AEB**" if wv["aeb"][i] > 0.5 else "")
        )
        st.caption("Drift angle and speed come from the sidebar. Drag the time slider to replay the run and see the LiDAR rays.")
