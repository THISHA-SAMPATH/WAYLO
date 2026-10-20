"""
WAYLO: Shared-Autonomy Spatial Mobility Copilot Dashboard
NVIDIA x Nebius Global AI Hackathon (Physical AI Track)
Accelerated with NVIDIA Nemotron-3-Ultra / Cosmos on Nebius AI Cloud
"""

import sys
import os
import json
import time
import math
import numpy as np
import requests
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge, Polygon
from matplotlib.lines import Line2D
import streamlit as st

# Ensure repository root is on sys.path for direct backend imports
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from backend.nebius_client import analyze_spatial_frame, get_api_key, compute_shared_autonomy_arbitration
from backend.tavily_search import fetch_accessibility_context, get_standard_specs

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="WAYLO | Shared-Autonomy Mobility Copilot",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Premium Custom Styling (Dark Mode, Glowing Accents, Clean Typography) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.3rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-bottom: 0px;
        background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .subtitle-badge {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 9999px;
        color: #7dd3fc;
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 12px;
    }
    
    .hud-card {
        background: #131b2e;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Top Header ---
col_head1, col_head2 = st.columns([2.5, 1.0])
with col_head1:
    st.markdown('<div class="main-title">♿ WAYLO: YOUR WORLD. YOUR WAY.</div>', unsafe_allow_html=True)
    st.markdown(
        '<span class="subtitle-badge">NVIDIA Nemotron-3-Ultra / Cosmos • Nebius Token Factory • Physical AI Shared-Autonomy</span>',
        unsafe_allow_html=True
    )
with col_head2:
    st.markdown("""
    <div style="text-align: right; padding-top: 8px;">
        <span style="font-size: 0.85rem; color: #94a3b8;">Differential Drive Chassis: <b>L=0.60m | r=0.16m</b></span><br>
        <span style="font-size: 0.82rem; color: #38bdf8;">FastAPI Backend: <b>http://localhost:8000</b></span>
    </div>
    """, unsafe_allow_html=True)

# --- Session State Initialization ---
if "inference_result" not in st.session_state:
    st.session_state["inference_result"] = None
if "last_params" not in st.session_state:
    st.session_state["last_params"] = None
if "cached_standards" not in st.session_state:
    st.session_state["cached_standards"] = fetch_accessibility_context()

# --- Sidebar Controls ---
st.sidebar.header("🕹️ Vehicle & Intent Controls")

backend_toggle = st.sidebar.radio(
    "Middleware Gateway:",
    ["Direct Python Client (Zero Latency)", "FastAPI REST Server (HTTP:8000)"],
    index=0
)

# API Configuration Expander
with st.sidebar.expander("☁️ Nebius AI Cloud Credentials", expanded=False):
    default_env_key = os.getenv("NEBIUS_API_KEY", "")
    api_key_input = st.text_input(
        "Nebius API Key:",
        value=default_env_key if default_env_key != "your_nebius_api_key_here" else "",
        type="password",
        help="Paste your Nebius Token Factory key. Leave blank for deterministic offline simulation."
    )
    base_url_input = st.text_input(
        "Nebius Base URL:",
        value=os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1")
    )
    model_choice = st.selectbox(
        "NVIDIA Model on Nebius:",
        ["nvidia/nemotron-3-ultra", "nvidia/cosmos-nemotron-34b", "meta-llama/Llama-3.3-70B-Instruct"]
    )

active_key = get_api_key(api_key_input)
if active_key:
    st.sidebar.success("🟢 Nebius Cloud: Connected")
else:
    st.sidebar.info("🟡 Mode: Local Deterministic Physics Sim")

scenario_name = st.sidebar.selectbox(
    "Target Indoor Scenario:",
    ["Align with Doorway", "Navigate Tight Corridor", "Dock at Table", "Emergency Stop Test"]
)

st.sidebar.subheader("🕹️ User Joystick Input")
manual_steering_deg = st.sidebar.slider("Manual Steering Drift Angle (°):", -45, 45, 14, step=1)
speed_input = st.sidebar.slider("Target Linear Velocity (m/s):", 0.0, 1.8, 0.85, step=0.05)

auto_recalculate = st.sidebar.checkbox("Real-Time Spatial Copilot Assist", value=True)
trigger_inference = st.sidebar.button("⚡ Run Spatial Inference", type="primary", use_container_width=True)

with st.sidebar.expander("⚙️ Physical Vehicle Specs", expanded=False):
    wheelbase_l = st.slider("Wheelbase L (meters):", 0.45, 0.80, 0.60, 0.05)
    wheel_radius_r = st.slider("Wheel Radius r (meters):", 0.10, 0.25, 0.16, 0.01)

# Inference execution
current_params = (scenario_name, manual_steering_deg, speed_input, model_choice)
should_execute = trigger_inference or (auto_recalculate and (
    st.session_state["inference_result"] is None or
    st.session_state["last_params"] != current_params
))

if should_execute:
    with st.spinner("Processing spatial perception frame..."):
        if "FastAPI" in backend_toggle:
            try:
                payload = {
                    "frame_metadata": f"stream_scenario_{scenario_name}",
                    "user_intent": scenario_name,
                    "steering_angle_deg": float(manual_steering_deg),
                    "velocity_mps": float(speed_input),
                    "query_accessibility": False
                }
                resp = requests.post("http://localhost:8000/api/spatial/analyze", json=payload, timeout=3.0)
                if resp.status_code == 200:
                    st.session_state["inference_result"] = resp.json()
                else:
                    raise Exception(f"HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                st.sidebar.warning(f"FastAPI offline. Direct Python client fallback active.")
                st.session_state["inference_result"] = analyze_spatial_frame(
                    image_payload=f"stream_scenario_{scenario_name}",
                    user_intent=scenario_name,
                    steering_deg=float(manual_steering_deg),
                    speed_mps=float(speed_input),
                    api_key=api_key_input if active_key else None,
                    base_url=base_url_input,
                    model=model_choice,
                    accessibility_context=st.session_state.get("cached_standards")
                )
        else:
            st.session_state["inference_result"] = analyze_spatial_frame(
                image_payload=f"stream_scenario_{scenario_name}",
                user_intent=scenario_name,
                steering_deg=float(manual_steering_deg),
                speed_mps=float(speed_input),
                api_key=api_key_input if active_key else None,
                base_url=base_url_input,
                model=model_choice,
                accessibility_context=st.session_state.get("cached_standards")
            )
        st.session_state["last_params"] = current_params

result = st.session_state.get("inference_result")

tab_cockpit, tab_kinematics, tab_tavily, tab_api = st.tabs([
    "🎮 Shared-Autonomy Cockpit",
    "🔬 Differential Kinematics & Alpha Blending",
    "🌐 Tavily ADA & ISO Standards",
    "⚡ API Telemetry & Nebius Inspector"
])

with tab_cockpit:
    col_vis, col_hud = st.columns([1.8, 1.2])

    with col_vis:
        st.subheader("🗺️ Spatial 2D Perception & Comparative Trajectories")
        fig, ax = plt.subplots(figsize=(7.5, 5.5), facecolor="#0b0f19")
        ax.set_facecolor("#111827")
        ax.set_xlim(-3.0, 3.0)
        ax.set_ylim(0.0, 6.2)

        chair_x, chair_y = 0.0, 0.8
        chair_w, chair_l = 0.55, 0.65

        if scenario_name == "Align with Doorway":
            ax.add_patch(Rectangle((-2.9, 4.4), 2.2, 0.25, color="#475569", zorder=3))
            ax.add_patch(Rectangle((0.7, 4.4), 2.2, 0.25, color="#475569", zorder=3))
            ax.plot([-0.7, 0.7], [4.5, 4.5], "--", color="#22c55e", linewidth=2.5, zorder=4)
            ax.plot([-0.7, 0.7], [4.5, 4.5], "s", color="#38bdf8", markersize=7, zorder=5)
            ax.text(0.0, 4.8, "DOORWAY (1.4m Opening)", color="#86efac", ha="center", fontsize=9, fontweight="bold")
        elif scenario_name == "Navigate Tight Corridor":
            ax.add_patch(Rectangle((-2.9, 1.8), 2.3, 4.0, color="#475569", zorder=3))
            ax.add_patch(Rectangle((0.6, 1.8), 2.3, 4.0, color="#475569", zorder=3))
            ax.plot([0.0, 0.0], [1.8, 5.8], ":", color="#38bdf8", linewidth=1.5, zorder=2)
            ax.text(0.0, 6.0, "Corridor Centerline (1.2m Width)", color="#7dd3fc", ha="center", fontsize=9)
        elif scenario_name == "Dock at Table":
            ax.add_patch(Rectangle((-1.4, 3.8), 2.8, 1.4, color="#9333ea", alpha=0.8, zorder=3))
            ax.plot([-0.5, 0.5], [3.8, 3.8], "--", color="#fbbf24", linewidth=2.5, zorder=4)
            ax.text(0.0, 4.5, "Workstation Desk", color="#f3e8ff", ha="center", fontsize=10, fontweight="bold")
            ax.text(0.0, 3.55, "Docking Target Slot", color="#fde047", ha="center", fontsize=9)
        elif scenario_name == "Emergency Stop Test":
            ax.add_patch(Rectangle((-2.9, 5.2), 5.8, 0.25, color="#475569", zorder=3))
            obs_circ = Circle((0.0, 2.5), 0.35, color="#ef4444", zorder=5)
            stop_boundary = Circle((0.0, 2.5), 0.85, fill=False, edgecolor="#f87171", linestyle="--", linewidth=1.5, zorder=4)
            ax.add_patch(obs_circ)
            ax.add_patch(stop_boundary)
            ax.text(0.0, 2.5, "⚠️", color="white", ha="center", va="center", fontsize=12)
            ax.text(0.0, 3.05, "Dynamic Obstacle Detected", color="#fca5a5", ha="center", fontsize=9, fontweight="bold")

        # Wheelchair geometry
        ax.add_patch(Rectangle((chair_x - 0.34, chair_y - 0.20), 0.08, 0.35, color="#1e293b", zorder=5))
        ax.add_patch(Rectangle((chair_x + 0.26, chair_y - 0.20), 0.08, 0.35, color="#1e293b", zorder=5))
        ax.add_patch(Rectangle((chair_x - chair_w/2, chair_y - chair_l/2), chair_w, chair_l, color="#2563eb", zorder=6))
        ax.add_patch(Rectangle((chair_x - 0.20, chair_y - 0.20), 0.40, 0.40, color="#60a5fa", zorder=7))
        ax.plot([chair_x - 0.22, chair_x + 0.22], [chair_y + 0.28, chair_y + 0.28], "o", color="#94a3b8", markersize=6, zorder=8)
        ax.plot(chair_x, chair_y, "o", color="white", markersize=5, zorder=9)

        # LiDAR fan
        lidar_range = 2.4
        for ang_deg in np.linspace(-35, 35, 9):
            rad = np.radians(90 - ang_deg)
            rx = chair_x + lidar_range * np.cos(rad)
            ry = chair_y + lidar_range * np.sin(rad)
            ax.plot([chair_x, rx], [chair_y + 0.3, ry], ":", color="#38bdf8", alpha=0.35, linewidth=1.0, zorder=3)

        # Vectors
        rad_user = np.radians(90 - manual_steering_deg)
        dist_user = 2.4
        dx_user = np.cos(rad_user) * dist_user
        dy_user = np.sin(rad_user) * dist_user
        ax.annotate(
            "", xy=(chair_x + dx_user, chair_y + dy_user), xytext=(chair_x, chair_y),
            arrowprops=dict(arrowstyle="->,head_width=0.45,head_length=0.7", color="#f43f5e", lw=2.8),
            zorder=10
        )

        if result:
            is_emergency = result.get("emergency_stop", False)
            if is_emergency:
                ax.plot(chair_x, chair_y + 0.45, "X", color="#ef4444", markersize=16, markeredgewidth=4, zorder=12)
                ax.text(chair_x, chair_y + 0.70, "AEB TRIGGERED: MOTORS HALTED", color="#ef4444", ha="center", fontsize=9, fontweight="bold")
            else:
                corr_deg = float(result.get("steering_correction_deg", 0.0))
                alpha = float(result.get("arbitration_alpha", 0.5))
                blended_angle_deg = manual_steering_deg + (alpha * corr_deg)
                rad_corr = np.radians(90 - blended_angle_deg)
                dist_corr = 3.6
                dx_corr = np.cos(rad_corr) * dist_corr
                dy_corr = np.sin(rad_corr) * dist_corr
                ax.annotate(
                    "", xy=(chair_x + dx_corr, chair_y + dy_corr), xytext=(chair_x, chair_y),
                    arrowprops=dict(arrowstyle="->,head_width=0.5,head_length=0.8", color="#22c55e", lw=3.2, linestyle="--"),
                    zorder=11
                )

        legend_handles = [
            Line2D([0], [0], marker="s", color="w", markerfacecolor="#2563eb", markersize=10, label="WAYLO Wheelchair"),
            Line2D([0], [0], color="#f43f5e", lw=2.8, label="Unassisted Path (Steering Drift)"),
            Line2D([0], [0], color="#22c55e", lw=3.2, linestyle="--", label="WAYLO Blended Trajectory (Centered)"),
            Line2D([0], [0], color="#475569", lw=6, label="Room Boundaries / Walls"),
        ]
        ax.legend(handles=legend_handles, loc="lower right", facecolor="#111827", edgecolor="#374151", labelcolor="white", fontsize=8.5)
        ax.grid(True, linestyle=":", alpha=0.25, color="#64748b")
        ax.tick_params(colors="#94a3b8")
        for spine in ax.spines.values():
            spine.set_color("#374151")
        ax.set_xlabel("Lateral X Distance (meters)", color="#94a3b8", fontsize=9)
        ax.set_ylabel("Forward Y Distance (meters)", color="#94a3b8", fontsize=9)
        st.pyplot(fig)
        plt.close(fig)

    with col_hud:
        st.subheader("📡 Real-Time Telemetry & Copilot HUD")
        if result:
            clearance_l = float(result.get("clearance_left", 0.40))
            clearance_r = float(result.get("clearance_right", 0.40))
            risk_score = int(result.get("hazard_risk_score", 10))
            alpha_val = float(result.get("arbitration_alpha", 0.50))
            is_emergency = bool(result.get("emergency_stop", False))
            rec_vel = result.get("recommended_velocity", f"{speed_input} m/s")
            correction = float(result.get("steering_correction_deg", 0.0))
            ttc = float(result.get("time_to_collision_sec", 2.5))

            c1, c2 = st.columns(2)
            c1.metric("Left Clearance", f"{clearance_l:.2f} m", delta=f"{clearance_l - 0.40:+.2f} m")
            c2.metric("Right Clearance", f"{clearance_r:.2f} m", delta=f"{clearance_r - 0.40:+.2f} m")

            c3, c4 = st.columns(2)
            c3.metric("Authority Alpha (α)", f"{alpha_val:.2f}", delta="Copilot Override" if alpha_val > 0.6 else "Shared")
            c4.metric("Hazard Risk", f"{risk_score}%", delta=f"{risk_score - 20:+d}%", delta_color="inverse")

            c5, c6 = st.columns(2)
            c5.metric("Copilot Speed", rec_vel, delta=result.get("speed_buffer_override", "NOMINAL"))
            c6.metric("Time-to-Collision", f"{ttc:.2f} s" if not is_emergency else "0.0 s", delta="CRITICAL" if ttc < 1.0 else "NOMINAL")

            st.markdown("---")
            if is_emergency:
                st.error("🚨 **CRITICAL: AUTONOMOUS EMERGENCY BRAKE (AEB) ACTIVATED**\nObstacle inside minimum braking safety distance.")
            elif abs(correction) > 3.0:
                st.warning(f"🔄 **SHARED-AUTONOMY CENTERING ACTIVE**\nApplying **{correction:+.1f}°** trajectory correction (Authority α = **{alpha_val:.2f}**).")
            else:
                st.success("✅ **TRAJECTORY NOMINAL**\nClearance envelope is safe.")

            st.info(f"**🧠 Spatial Reasoning Advisory:**\n\n{result.get('spatial_summary', '')}")
            src = result.get("source", "simulated")
            src_str = "🟢 Nebius AI Cloud (Live Token Factory)" if "nebius" in src else "🟡 Deterministic Physical Sim Engine"
            st.caption(f"**Source:** {src_str} | **Model:** `{result.get('model', 'nvidia/nemotron-3-ultra')}`")

with tab_kinematics:
    st.subheader("🔬 Mathematical Formulation: Shared Autonomy Arbitration")
    st.latex(r"\mathbf{v}_{\text{final}} = (1 - \alpha) \mathbf{v}_{\text{user}} + \alpha \mathbf{v}_{\text{copilot}}")
    st.latex(r"\theta_{\text{final}} = \theta_{\text{user}} + \alpha \cdot \Delta \theta_{\text{copilot}}")
    st.markdown(r"""Where dynamic arbitration weight $\alpha \in [0.0, 1.0]$ scales with perceived hazard risk and clearance deficit.""")

with tab_tavily:
    st.subheader("🌐 Real-Time Spatial Standards Retrieval via Tavily Search API")
    st.info(st.session_state.get("cached_standards", "No standards cached yet."))
    specs = get_standard_specs()
    st.json(specs)

with tab_api:
    st.subheader("⚡ Middleware Status & Raw Telemetry Payloads")
    if result:
        st.json(result)