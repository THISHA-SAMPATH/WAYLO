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
    
    .metric-value-highlight {
        font-family: 'Outfit', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
    }
    
    .status-pill-safe {
        background-color: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .status-pill-warn {
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .status-pill-danger {
        background-color: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.85rem;
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
if "backend_mode" not in st.session_state:
    st.session_state["backend_mode"] = "Direct Python Client"

# --- Sidebar Controls ---
st.sidebar.header("🕹️ Vehicle & Intent Controls")

# Backend Selection
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
        value=os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1")
    )
    model_choice = st.selectbox(
        "NVIDIA Model on Nebius:",
        ["nvidia/Nemotron-3-Ultra-550b-a55b", "nvidia/nemotron-3-super-120b-a12b", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "nvidia/Cosmos3-Super-Reasoner"]
    )

# Connection Status Indicator
active_key = get_api_key(api_key_input)
if active_key:
    st.sidebar.success("🟢 Nebius Cloud: Connected")
else:
    st.sidebar.info("🟡 Mode: Local Deterministic Physics Sim")

# Testing Scenario Selector
scenario_name = st.sidebar.selectbox(
    "Target Indoor Scenario:",
    ["Align with Doorway", "Navigate Tight Corridor", "Dock at Table", "Emergency Stop Test"]
)

st.sidebar.subheader("🕹️ User Joystick Input")
manual_steering_deg = st.sidebar.slider("Manual Steering Drift Angle (°):", -45, 45, 14, step=1)
speed_input = st.sidebar.slider("Target Linear Velocity (m/s):", 0.0, 1.8, 0.85, step=0.05)

# Copilot Assistance Setting
auto_recalculate = st.sidebar.checkbox("Real-Time Spatial Copilot Assist", value=True)
trigger_inference = st.sidebar.button("⚡ Run Spatial Inference", type="primary", use_container_width=True)

# Kinematics Parameters Expander
with st.sidebar.expander("⚙️ Physical Vehicle Specs", expanded=False):
    wheelbase_l = st.slider("Wheelbase L (meters):", 0.45, 0.80, 0.60, 0.05)
    wheel_radius_r = st.slider("Wheel Radius r (meters):", 0.10, 0.25, 0.16, 0.01)
    max_accel = st.slider("Max Deceleration a_max (m/s²):", 1.0, 3.5, 2.0, 0.2)

# --- Inference Execution Logic ---
current_params = (scenario_name, manual_steering_deg, speed_input, model_choice)
should_execute = trigger_inference or (auto_recalculate and (
    st.session_state["inference_result"] is None or
    st.session_state["last_params"] != current_params
))

if should_execute:
    with st.spinner("Processing spatial perception frame..."):
        if "FastAPI" in backend_toggle:
            # Query local FastAPI endpoint
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
                st.sidebar.warning(f"FastAPI offline ({e}). Using direct Python client fallback.")
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
            # Direct Python backend call
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

# --- Tabs Structure ---
tab_cockpit, tab_kinematics, tab_tavily, tab_api, tab_closed = st.tabs([
    "🎮 Shared-Autonomy Cockpit",
    "🔬 Differential Kinematics & Alpha Blending",
    "🌐 Tavily ADA & ISO Standards",
    "⚡ API Telemetry & Nebius Inspector",
    "🚪 Closed-Loop Doorway Run"
])

# ==============================================================================
# TAB 1: SHARED-AUTONOMY COCKPIT
# ==============================================================================
with tab_cockpit:
    col_vis, col_hud = st.columns([1.8, 1.2])

    with col_vis:
        st.subheader("🗺️ Spatial 2D Perception & Comparative Trajectories")

        # Create High-Aesthetic Dark Theme Matplotlib Plot
        fig, ax = plt.subplots(figsize=(7.5, 5.5), facecolor="#0b0f19")
        ax.set_facecolor("#111827")
        ax.set_xlim(-3.0, 3.0)
        ax.set_ylim(0.0, 6.2)

        # Baseline Wheelchair Coordinates
        chair_x, chair_y = 0.0, 0.8
        chair_w, chair_l = 0.55, 0.65

        # Render Environment based on Scenario
        if scenario_name == "Align with Doorway":
            # 1.4m central opening between Y=4.5m
            ax.add_patch(Rectangle((-2.9, 4.4), 2.2, 0.25, color="#475569", zorder=3))
            ax.add_patch(Rectangle((0.7, 4.4), 2.2, 0.25, color="#475569", zorder=3))
            # Green threshold line
            ax.plot([-0.7, 0.7], [4.5, 4.5], "--", color="#22c55e", linewidth=2.5, zorder=4)
            # Doorway posts markers
            ax.plot([-0.7, 0.7], [4.5, 4.5], "s", color="#38bdf8", markersize=7, zorder=5)
            ax.text(0.0, 4.8, "DOORWAY (1.4m Opening)", color="#86efac", ha="center", fontsize=9, fontweight="bold")

        elif scenario_name == "Navigate Tight Corridor":
            # 1.2m narrow corridor from Y=1.8m to Y=5.8m
            ax.add_patch(Rectangle((-2.9, 1.8), 2.3, 4.0, color="#475569", zorder=3))
            ax.add_patch(Rectangle((0.6, 1.8), 2.3, 4.0, color="#475569", zorder=3))
            ax.plot([0.0, 0.0], [1.8, 5.8], ":", color="#38bdf8", linewidth=1.5, zorder=2)
            ax.text(0.0, 6.0, "Corridor Centerline (1.2m Width)", color="#7dd3fc", ha="center", fontsize=9)

        elif scenario_name == "Dock at Table":
            # Workstation desk at Y=3.8m
            ax.add_patch(Rectangle((-1.4, 3.8), 2.8, 1.4, color="#9333ea", alpha=0.8, zorder=3))
            ax.plot([-0.5, 0.5], [3.8, 3.8], "--", color="#fbbf24", linewidth=2.5, zorder=4)
            ax.text(0.0, 4.5, "Workstation Desk", color="#f3e8ff", ha="center", fontsize=10, fontweight="bold")
            ax.text(0.0, 3.55, "Docking Target Slot", color="#fde047", ha="center", fontsize=9)

        elif scenario_name == "Emergency Stop Test":
            # Dynamic obstacle at Y=2.5m
            ax.add_patch(Rectangle((-2.9, 5.2), 5.8, 0.25, color="#475569", zorder=3))
            obs_circ = Circle((0.0, 2.5), 0.35, color="#ef4444", zorder=5)
            stop_boundary = Circle((0.0, 2.5), 0.85, fill=False, edgecolor="#f87171", linestyle="--", linewidth=1.5, zorder=4)
            ax.add_patch(obs_circ)
            ax.add_patch(stop_boundary)
            ax.text(0.0, 2.5, "⚠️", color="white", ha="center", va="center", fontsize=12)
            ax.text(0.0, 3.05, "Dynamic Obstacle Detected", color="#fca5a5", ha="center", fontsize=9, fontweight="bold")

        # Draw Electric Wheelchair Model
        # Drive Wheels (Left & Right)
        ax.add_patch(Rectangle((chair_x - 0.34, chair_y - 0.20), 0.08, 0.35, color="#1e293b", zorder=5))
        ax.add_patch(Rectangle((chair_x + 0.26, chair_y - 0.20), 0.08, 0.35, color="#1e293b", zorder=5))
        # Chassis body
        ax.add_patch(Rectangle((chair_x - chair_w/2, chair_y - chair_l/2), chair_w, chair_l, color="#2563eb", zorder=6))
        # Seat cushion
        ax.add_patch(Rectangle((chair_x - 0.20, chair_y - 0.20), 0.40, 0.40, color="#60a5fa", zorder=7))
        # Front Casters
        ax.plot([chair_x - 0.22, chair_x + 0.22], [chair_y + 0.28, chair_y + 0.28], "o", color="#94a3b8", markersize=6, zorder=8)
        # Center marker
        ax.plot(chair_x, chair_y, "o", color="white", markersize=5, zorder=9)

        # Draw LiDAR Perception Ray Sweep (Fan of 9 rays)
        lidar_range = 2.4
        for ang_deg in np.linspace(-35, 35, 9):
            rad = np.radians(90 - ang_deg)
            rx = chair_x + lidar_range * np.cos(rad)
            ry = chair_y + lidar_range * np.sin(rad)
            ax.plot([chair_x, rx], [chair_y + 0.3, ry], ":", color="#38bdf8", alpha=0.35, linewidth=1.0, zorder=3)

        # 1. Unassisted Trajectory (Red Path - Human Alone)
        rad_user = np.radians(90 - manual_steering_deg)
        dist_user = 2.4
        dx_user = np.cos(rad_user) * dist_user
        dy_user = np.sin(rad_user) * dist_user
        ax.annotate(
            "", xy=(chair_x + dx_user, chair_y + dy_user), xytext=(chair_x, chair_y),
            arrowprops=dict(arrowstyle="->,head_width=0.45,head_length=0.7", color="#f43f5e", lw=2.8),
            zorder=10
        )

        # 2. WAYLO Shared-Autonomy Corrected Trajectory (Green Path)
        if result:
            is_emergency = result.get("emergency_stop", False)
            if is_emergency:
                # Emergency Stop Marker
                ax.plot(chair_x, chair_y + 0.45, "X", color="#ef4444", markersize=16, markeredgewidth=4, zorder=12)
                ax.text(chair_x, chair_y + 0.70, "AEB TRIGGERED: MOTORS HALTED", color="#ef4444", ha="center", fontsize=9, fontweight="bold")
            else:
                corr_deg = float(result.get("steering_correction_deg", 0.0))
                alpha = float(result.get("arbitration_alpha", 0.5))
                # Blended angle
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

        # Clean Legend
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

            # Row 1: Clearance Margins
            c1, c2 = st.columns(2)
            c1.metric("Left Clearance", f"{clearance_l:.2f} m", delta=f"{clearance_l - 0.40:+.2f} m")
            c2.metric("Right Clearance", f"{clearance_r:.2f} m", delta=f"{clearance_r - 0.40:+.2f} m")

            # Row 2: Blending Alpha & Risk
            c3, c4 = st.columns(2)
            c3.metric("Authority Alpha (α)", f"{alpha_val:.2f}", delta="Copilot Override" if alpha_val > 0.6 else "Shared")
            c4.metric("Hazard Risk", f"{risk_score}%", delta=f"{risk_score - 20:+d}%", delta_color="inverse")

            # Row 3: Velocity & Time-to-Collision
            c5, c6 = st.columns(2)
            c5.metric("Copilot Speed", rec_vel, delta=result.get("speed_buffer_override", "NOMINAL"))
            c6.metric("Time-to-Collision", f"{ttc:.2f} s" if not is_emergency else "0.0 s", delta="CRITICAL" if ttc < 1.0 else "NOMINAL")

            st.markdown("---")

            # Status Banner
            if is_emergency:
                st.error("🚨 **CRITICAL: AUTONOMOUS EMERGENCY BRAKE (AEB) ACTIVATED**\nObstacle inside minimum braking safety distance. Motor torque cut to 0%.")
            elif abs(correction) > 3.0:
                st.warning(f"🔄 **SHARED-AUTONOMY CENTERING ACTIVE**\nApplying **{correction:+.1f}°** trajectory correction (Authority α = **{alpha_val:.2f}**).")
            else:
                st.success("✅ **TRAJECTORY NOMINAL**\nClearance envelope is safe. Full manual steering authority granted to user.")

            # Copilot Natural Language Advisory
            st.info(f"**🧠 Spatial Reasoning Advisory:**\n\n{result.get('spatial_summary', '')}")

            # Model & Source Badge
            src = result.get("source", "simulated")
            src_str = "🟢 Nebius AI Cloud (Live Token Factory)" if "nebius" in src else "🟡 Deterministic Physical Sim Engine"
            st.caption(f"**Source:** {src_str} | **Model:** `{result.get('model', 'nvidia/Nemotron-3-Ultra-550b-a55b')}`")

        else:
            st.info("Click '⚡ Run Spatial Inference' or adjust controls to compute copilot vectors.")

# ==============================================================================
# TAB 2: DIFFERENTIAL KINEMATICS & ALPHA BLENDING
# ==============================================================================
with tab_kinematics:
    st.subheader("🔬 Mathematical Formulation: Shared Autonomy Arbitration")
    st.markdown(r"""
    The WAYLO copilot continuously arbitrates between the human driver's joystick vector $\mathbf{v}_{\text{user}}$ and the AI's collision-free trajectory vector $\mathbf{v}_{\text{copilot}}$:
    """)

    st.latex(r"\mathbf{v}_{\text{final}} = (1 - \alpha) \mathbf{v}_{\text{user}} + \alpha \mathbf{v}_{\text{copilot}}")
    st.latex(r"\theta_{\text{final}} = \theta_{\text{user}} + \alpha \cdot \Delta \theta_{\text{copilot}}")

    st.markdown(r"""
    Where the dynamic arbitration weight $\alpha \in [0.0, 1.0]$ scales with perceived hazard risk $R$ and doorway clearance deficit:
    """)
    st.latex(r"\alpha = \mathrm{clip}\left(0.55 \frac{R}{100} + 0.45 \max\left(0, \frac{d_{\text{safe}} - d_{\min}}{d_{\text{safe}}}\right), 0.0, 1.0\right)")

    st.divider()

    # Differential Drive Calculations
    st.subheader("⚙️ Differential Drive Wheel Speeds Calculator")
    k_col1, k_col2, k_col3 = st.columns(3)

    curr_alpha = float(result.get("arbitration_alpha", 0.5)) if result else 0.5
    curr_corr = float(result.get("steering_correction_deg", 0.0)) if result else 0.0
    is_stop = bool(result.get("emergency_stop", False)) if result else False

    blended_v = 0.0 if is_stop else (1.0 - curr_alpha) * speed_input + curr_alpha * min(speed_input, 0.65)
    blended_steer = manual_steering_deg + (curr_alpha * curr_corr)
    rad_s = math.radians(blended_steer)
    omega = (blended_v / wheelbase_l) * math.tan(rad_s) if not is_stop else 0.0

    v_r = blended_v + (omega * wheelbase_l / 2.0)
    v_l = blended_v - (omega * wheelbase_l / 2.0)
    w_r = v_r / wheel_radius_r
    w_l = v_l / wheel_radius_r

    k_col1.metric("Blended Linear Velocity", f"{blended_v:.2f} m/s")
    k_col2.metric("Left Wheel Speed (ω_L)", f"{w_l:.2f} rad/s", f"{v_l:.2f} m/s")
    k_col3.metric("Right Wheel Speed (ω_R)", f"{w_r:.2f} rad/s", f"{v_r:.2f} m/s")

    # Interactive Wheel Speed Curves Plot
    fig_kin, ax_k = plt.subplots(figsize=(8, 3.2), facecolor="#0b0f19")
    ax_k.set_facecolor("#111827")
    angles = np.linspace(-30, 30, 100)
    omegas = (blended_v / wheelbase_l) * np.tan(np.radians(angles))
    vl_curve = (blended_v - (omegas * wheelbase_l / 2.0)) / wheel_radius_r
    vr_curve = (blended_v + (omegas * wheelbase_l / 2.0)) / wheel_radius_r

    ax_k.plot(angles, vl_curve, label="Left Wheel (ω_L)", color="#38bdf8", lw=2.2)
    ax_k.plot(angles, vr_curve, label="Right Wheel (ω_R)", color="#f59e0b", lw=2.2)
    ax_k.axvline(blended_steer, color="#22c55e", linestyle="--", label=f"Current Steer ({blended_steer:+.1f}°)")
    ax_k.set_xlabel("Effective Steering Angle (degrees)", color="#94a3b8")
    ax_k.set_ylabel("Wheel Speed (rad/s)", color="#94a3b8")
    ax_k.grid(True, linestyle=":", alpha=0.3, color="#64748b")
    ax_k.tick_params(colors="#94a3b8")
    for spine in ax_k.spines.values():
        spine.set_color("#374151")
    ax_k.legend(facecolor="#111827", edgecolor="#374151", labelcolor="white")
    st.pyplot(fig_kin)
    plt.close(fig_kin)

# ==============================================================================
# TAB 3: TAVILY ADA & ISO STANDARDS
# ==============================================================================
with tab_tavily:
    st.subheader("🌐 Real-Time Spatial Standards Retrieval via Tavily Search API")
    st.markdown("""
    WAYLO consults building codes and spatial accessibility standards (ADA Title III, ISO 7176) to inform NVIDIA Nemotron / Cosmos of ground-truth clearance requirements.
    """)

    t_col1, t_col2 = st.columns([2.5, 1.0])
    with t_col1:
        query_input = st.text_input(
            "Search Accessibility Building Codes:",
            value="ADA wheelchair doorway minimum clear opening width standard",
            help="Queries Tavily API for live regulation specifications"
        )
    with t_col2:
        st.write("")
        st.write("")
        search_btn = st.button("🔍 Search Standards", type="primary", use_container_width=True)

    if search_btn:
        with st.spinner("Querying Tavily Search API..."):
            st.session_state["cached_standards"] = fetch_accessibility_context(query_input)
            st.success("Retrieved live accessibility context!")

    st.markdown("### 📋 Active Standards Context Fed to Nebius Models:")
    st.info(st.session_state.get("cached_standards", "No standards cached yet."))

    st.markdown("### 📐 Ground-Truth Accessibility Catalog:")
    specs = get_standard_specs()
    sp_col1, sp_col2 = st.columns(2)
    with sp_col1:
        st.markdown(f"""
        **Doorway Clearance:**
        - Standard: `{specs['doorway']['standard_code']}`
        - Min Width: **{specs['doorway']['min_width_meters']} m** (32 inches)
        - Note: {specs['doorway']['guideline']}
        
        **Corridor Clearance:**
        - Standard: `{specs['corridor']['standard_code']}`
        - Min Width: **{specs['corridor']['min_width_meters']} m** (36 inches)
        - Note: {specs['corridor']['guideline']}
        """)
    with sp_col2:
        st.markdown(f"""
        **Circular Turning Space:**
        - Standard: `{specs['turning_radius']['standard_code']}`
        - Min Diameter: **{specs['turning_radius']['min_diameter_meters']} m** (60 inches)
        - Note: {specs['turning_radius']['guideline']}
        
        **Maximum Ramp Slope:**
        - Standard: `{specs['ramp_slope']['standard_code']}`
        - Ratio: **{specs['ramp_slope']['max_ratio']}** (8.33% slope)
        - Note: {specs['ramp_slope']['guideline']}
        """)

# ==============================================================================
# TAB 4: API TELEMETRY & NEBIUS INSPECTOR
# ==============================================================================
with tab_api:
    st.subheader("⚡ Middleware Status & Raw Telemetry Payloads")

    api_col1, api_col2 = st.columns(2)

    with api_col1:
        st.markdown("#### 🔗 FastAPI REST Endpoints (`http://localhost:8000`)")
        try:
            health_check = requests.get("http://localhost:8000/health", timeout=1.0).json()
            st.success(f"🟢 **FastAPI Server Online** (Status: `{health_check.get('status')}`)")
            st.json(health_check)
        except Exception:
            st.warning("🟡 **FastAPI Server Not Running Locally**\nLaunch with `python -m backend.main` or `uvicorn backend.main:app`")

    with api_col2:
        st.markdown("#### 📦 Latest Spatial Inference JSON Payload")
        if result:
            st.json(result)
        else:
            st.info("No inference payload generated yet.")

# ==============================================================================
# TAB 5: CLOSED-LOOP DOORWAY RUN (simulated LiDAR, unassisted vs WAYLO)
# ==============================================================================
with tab_closed:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from closed_loop_tab import render_closed_loop
    render_closed_loop(default_drift=manual_steering_deg, default_speed=speed_input)
