"""
WAYLO: YOUR WORLD. YOUR WAY.
Dark-Mode Streamlit Dashboard Visualizer & Telemetry Monitor
Powered by NVIDIA Nemotron / Cosmos on Nebius AI Cloud & Tavily Search API
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

# --- 1. Streamlit Page Configuration ---
st.set_page_config(
    page_title="WAYLO: YOUR WORLD. YOUR WAY.",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Dark Mode Custom Styling ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.4rem;
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

    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Top Header ---
col_head1, col_head2 = st.columns([2.6, 1.0])
with col_head1:
    st.markdown('<div class="main-title">♿ WAYLO: YOUR WORLD. YOUR WAY.</div>', unsafe_allow_html=True)
    st.markdown(
        '<span class="subtitle-badge">NVIDIA Nemotron / Cosmos • Nebius Token Factory • Shared-Autonomy Spatial Copilot</span>',
        unsafe_allow_html=True
    )
with col_head2:
    st.markdown("""
    <div style="text-align: right; padding-top: 10px;">
        <span style="font-size: 0.85rem; color: #94a3b8;">Chassis Track: <b>L=0.60m | r=0.16m</b></span><br>
        <span style="font-size: 0.82rem; color: #38bdf8;">Middleware API: <b>http://localhost:8000</b></span>
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

# --- 2. Sidebar Controls ---
st.sidebar.header("🕹️ Vehicle Intent & Joystick Controls")

# Vehicle Intent Selection
scenario_name = st.sidebar.selectbox(
    "Vehicle Navigational Intent:",
    ["Align with Doorway", "Navigate Corridor", "Dock at Table", "Emergency Stop Test"],
    index=0
)

# Steering and Velocity Sliders
manual_steering_deg = st.sidebar.slider(
    "Manual Steering Angle (°):",
    min_value=-45,
    max_value=45,
    value=14,
    step=1,
    help="Driver's raw joystick steering angle command"
)

speed_input = st.sidebar.slider(
    "Target Velocity (m/s):",
    min_value=0.0,
    max_value=2.0,
    value=0.85,
    step=0.05,
    help="Target forward velocity command"
)

# Gateway Selection
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
        value=default_env_key if default_env_key not in ("your_nebius_api_key_here", "") else "",
        type="password",
        help="Paste your Nebius Token Factory key. Leave blank for deterministic offline simulation."
    )
    base_url_input = st.text_input(
        "Nebius Base URL:",
        value=os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1")
    )
    model_choice = st.selectbox(
        "NVIDIA Model on Nebius:",
        ["nvidia/nemotron-3-ultra", "nvidia/Nemotron-3-Ultra-550b-a55b", "nvidia/nemotron-3-super-120b-a12b", "nvidia/Cosmos3-Super-Reasoner"]
    )

active_key = get_api_key(api_key_input)
if active_key:
    st.sidebar.success("🟢 Nebius Cloud: Connected")
else:
    st.sidebar.info("🟡 Mode: Local Deterministic Physics Sim")

# Physical specs expander
with st.sidebar.expander("⚙️ Physical Vehicle Specs", expanded=False):
    wheelbase_l = st.slider("Wheelbase L (meters):", 0.45, 0.80, 0.60, 0.05)
    wheel_radius_r = st.slider("Wheel Radius r (meters):", 0.10, 0.25, 0.16, 0.01)
    max_accel = st.slider("Max Deceleration a_max (m/s²):", 1.0, 3.5, 2.0, 0.2)

auto_recalculate = st.sidebar.checkbox("Real-Time Spatial Copilot Assist", value=True)
trigger_inference = st.sidebar.button("⚡ Run Spatial Inference", type="primary", use_container_width=True)

# --- 3. Inference Execution Logic ---
current_params = (scenario_name, manual_steering_deg, speed_input, model_choice)
should_execute = trigger_inference or (auto_recalculate and (
    st.session_state["inference_result"] is None or
    st.session_state["last_params"] != current_params
))

if should_execute:
    with st.spinner("Executing spatial perception inference..."):
        if "FastAPI" in backend_toggle:
            try:
                payload = {
                    "user_intent": scenario_name,
                    "manual_steering_deg": float(manual_steering_deg),
                    "speed_input": float(speed_input),
                    "current_pose_x": 0.0,
                    "current_pose_y": 1.0
                }
                resp = requests.post("http://localhost:8000/api/v1/copilot-step", json=payload, timeout=3.0)
                if resp.status_code == 200:
                    st.session_state["inference_result"] = resp.json()
                else:
                    raise Exception(f"HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                st.sidebar.warning(f"FastAPI error ({e}). Using direct Python client.")
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

# --- Tabs Structure ---
tab_cockpit, tab_kinematics, tab_tavily, tab_api, tab_closed = st.tabs([
    "🎮 Shared-Autonomy Cockpit",
    "🔬 Differential Kinematics & Alpha Blending",
    "🌐 Tavily ADA & ISO Standards",
    "⚡ Live Nebius AI JSON & API Telemetry",
    "🚪 Closed-Loop Doorway Run"
])

# ==============================================================================
# TAB 1: SHARED-AUTONOMY COCKPIT
# ==============================================================================
with tab_cockpit:
    col_vis, col_hud = st.columns([1.8, 1.2])

    with col_vis:
        st.subheader("🗺️ 2D Spatial Perception Grid")

        # Create Dark Theme Matplotlib Plot
        fig, ax = plt.subplots(figsize=(7.5, 5.5), facecolor="#0b0f19")
        ax.set_facecolor("#111827")
        ax.set_xlim(-3.0, 3.0)
        ax.set_ylim(0.0, 6.2)

        # Wheelchair Base Position: (X=0, Y=1) as specified
        chair_x, chair_y = 0.0, 1.0
        chair_w, chair_l = 0.55, 0.65

        # Render 1.4m Target Doorway and Room Walls
        if "Doorway" in scenario_name or "door" in scenario_name.lower():
            # 1.4m central opening between X = -0.7m and X = +0.7m at Y = 4.5m
            # Left room wall
            ax.add_patch(Rectangle((-3.0, 4.4), 2.3, 0.25, color="#475569", zorder=3))
            # Right room wall
            ax.add_patch(Rectangle((0.7, 4.4), 2.3, 0.25, color="#475569", zorder=3))
            # Green doorway threshold
            ax.plot([-0.7, 0.7], [4.5, 4.5], "--", color="#22c55e", linewidth=2.5, zorder=4)
            # Doorway posts markers
            ax.plot([-0.7, 0.7], [4.5, 4.5], "s", color="#38bdf8", markersize=8, zorder=5)
            ax.text(0.0, 4.8, "TARGET DOORWAY (1.4m Opening)", color="#86efac", ha="center", fontsize=9.5, fontweight="bold")

        elif "Corridor" in scenario_name:
            # Narrow corridor walls
            ax.add_patch(Rectangle((-3.0, 1.8), 2.4, 4.0, color="#475569", zorder=3))
            ax.add_patch(Rectangle((0.6, 1.8), 2.4, 4.0, color="#475569", zorder=3))
            ax.plot([0.0, 0.0], [1.8, 5.8], ":", color="#38bdf8", linewidth=1.5, zorder=2)
            ax.text(0.0, 6.0, "Corridor Centerline (1.2m Width)", color="#7dd3fc", ha="center", fontsize=9)

        elif "Table" in scenario_name:
            ax.add_patch(Rectangle((-1.4, 3.8), 2.8, 1.4, color="#9333ea", alpha=0.8, zorder=3))
            ax.plot([-0.5, 0.5], [3.8, 3.8], "--", color="#fbbf24", linewidth=2.5, zorder=4)
            ax.text(0.0, 4.5, "Workstation Desk", color="#f3e8ff", ha="center", fontsize=10, fontweight="bold")
            ax.text(0.0, 3.55, "Docking Target Slot", color="#fde047", ha="center", fontsize=9)

        else:
            ax.add_patch(Rectangle((-3.0, 5.2), 6.0, 0.25, color="#475569", zorder=3))
            obs_circ = Circle((0.0, 2.5), 0.35, color="#ef4444", zorder=5)
            stop_boundary = Circle((0.0, 2.5), 0.85, fill=False, edgecolor="#f87171", linestyle="--", linewidth=1.5, zorder=4)
            ax.add_patch(obs_circ)
            ax.add_patch(stop_boundary)
            ax.text(0.0, 2.5, "⚠️", color="white", ha="center", va="center", fontsize=12)
            ax.text(0.0, 3.05, "Dynamic Obstacle Detected", color="#fca5a5", ha="center", fontsize=9, fontweight="bold")

        # Side boundary walls
        ax.add_patch(Rectangle((-3.0, 0.0), 0.15, 6.2, color="#334155", zorder=2))
        ax.add_patch(Rectangle((2.85, 0.0), 0.15, 6.2, color="#334155", zorder=2))

        # Draw Wheelchair Chassis at Base Position (X=0, Y=1)
        ax.add_patch(Rectangle((chair_x - 0.34, chair_y - 0.20), 0.08, 0.35, color="#1e293b", zorder=5))
        ax.add_patch(Rectangle((chair_x + 0.26, chair_y - 0.20), 0.08, 0.35, color="#1e293b", zorder=5))
        ax.add_patch(Rectangle((chair_x - chair_w/2, chair_y - chair_l/2), chair_w, chair_l, color="#2563eb", zorder=6))
        ax.add_patch(Rectangle((chair_x - 0.20, chair_y - 0.20), 0.40, 0.40, color="#60a5fa", zorder=7))
        ax.plot([chair_x - 0.22, chair_x + 0.22], [chair_y + 0.28, chair_y + 0.28], "o", color="#94a3b8", markersize=6, zorder=8)
        ax.plot(chair_x, chair_y, "o", color="white", markersize=5, zorder=9)

        # 1. Manual Joystick Vector: Red Arrow
        rad_user = np.radians(90 - manual_steering_deg)
        dist_user = 2.2
        dx_user = np.cos(rad_user) * dist_user
        dy_user = np.sin(rad_user) * dist_user
        ax.annotate(
            "", xy=(chair_x + dx_user, chair_y + dy_user), xytext=(chair_x, chair_y),
            arrowprops=dict(arrowstyle="->,head_width=0.45,head_length=0.7", color="#f43f5e", lw=2.8),
            zorder=10
        )

        # 2. WAYLO Corrected Vector: Green Dashed Arrow
        if result:
            is_emergency = result.get("emergency_stop", False)
            if is_emergency:
                ax.plot(chair_x, chair_y + 0.45, "X", color="#ef4444", markersize=16, markeredgewidth=4, zorder=12)
                ax.text(chair_x, chair_y + 0.70, "AEB TRIGGERED: MOTORS HALTED", color="#ef4444", ha="center", fontsize=9, fontweight="bold")
            else:
                corr_deg = float(result.get("steering_correction_deg", 8.5))
                alpha = float(result.get("arbitration_alpha", result.get("alpha", 0.5)))
                blended_angle_deg = manual_steering_deg + (alpha * corr_deg)
                rad_corr = np.radians(90 - blended_angle_deg)
                dist_corr = 3.2
                dx_corr = np.cos(rad_corr) * dist_corr
                dy_corr = np.sin(rad_corr) * dist_corr
                ax.annotate(
                    "", xy=(chair_x + dx_corr, chair_y + dy_corr), xytext=(chair_x, chair_y),
                    arrowprops=dict(arrowstyle="->,head_width=0.5,head_length=0.8", color="#22c55e", lw=3.2, linestyle="--"),
                    zorder=11
                )

        # Legend and Axis Styling
        legend_handles = [
            Line2D([0], [0], marker="s", color="w", markerfacecolor="#2563eb", markersize=10, label="Wheelchair Base (X=0, Y=1)"),
            Line2D([0], [0], color="#f43f5e", lw=2.8, label="Manual Joystick Vector (Red)"),
            Line2D([0], [0], color="#22c55e", lw=3.2, linestyle="--", label="WAYLO Corrected Vector (Green Dashed)"),
            Line2D([0], [0], color="#475569", lw=6, label="Room Walls / 1.4m Doorway"),
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
        st.subheader("📡 Telemetry HUD & Metrics")

        # Telemetry Metric Cards: Left Clearance, Right Clearance, and Hazard Risk Index
        clearance_l = float(result.get("clearance_left_m", result.get("clearance_left", 0.42))) if result else 0.42
        clearance_r = float(result.get("clearance_right_m", result.get("clearance_right", 0.38))) if result else 0.38
        risk_score = int(result.get("hazard_risk_score", 12)) if result else 12

        col_m1, col_m2 = st.columns(2)
        col_m1.metric(
            label="Left Clearance",
            value=f"{clearance_l:.2f} m",
            delta=f"{clearance_l - 0.40:+.2f} m vs buffer"
        )
        col_m2.metric(
            label="Right Clearance",
            value=f"{clearance_r:.2f} m",
            delta=f"{clearance_r - 0.40:+.2f} m vs buffer"
        )

        col_m3, col_m4 = st.columns(2)
        col_m3.metric(
            label="Hazard Risk Index",
            value=f"{risk_score}%",
            delta=f"{risk_score - 20:+d}% danger",
            delta_color="inverse"
        )
        alpha_disp = float(result.get("arbitration_alpha", result.get("alpha", 0.5))) if result else 0.5
        col_m4.metric(
            label="Arbitration Alpha (α)",
            value=f"{alpha_disp:.2f}",
            delta="Copilot Active" if alpha_disp > 0.4 else "Driver Primary"
        )

        st.markdown("---")

        # Live Status Advisory
        if result:
            is_emergency = bool(result.get("emergency_stop", False))
            corr = float(result.get("steering_correction_deg", 8.5))
            if is_emergency:
                st.error("🚨 **AUTONOMOUS EMERGENCY BRAKE ACTIVATED** — Vehicle halted.")
            elif abs(corr) > 3.0:
                st.warning(f"🔄 **SHARED-AUTONOMY CORRECTION ACTIVE**: Applying **{corr:+.1f}°** steering compensation.")
            else:
                st.success("✅ **CLEARANCE NOMINAL**: Driver maintaining centered trajectory.")

            st.info(f"**🧠 Spatial Summary:**\n\n{result.get('spatial_summary', '')}")

# ==============================================================================
# TAB 2: DIFFERENTIAL KINEMATICS & ALPHA BLENDING
# ==============================================================================
with tab_kinematics:
    st.subheader("🔬 Shared Autonomy Kinematics & Wheel Arbitration")
    st.markdown(r"""
    The copilot performs linear and angular arbitration:
    $$\mathbf{v}_{\text{final}} = (1 - \alpha) \mathbf{v}_{\text{user}} + \alpha \mathbf{v}_{\text{copilot}}$$
    $$\theta_{\text{final}} = (1 - \alpha) \theta_{\text{user}} + \alpha \theta_{\text{copilot}}$$
    """)

    k_col1, k_col2, k_col3 = st.columns(3)
    curr_alpha = float(result.get("arbitration_alpha", result.get("alpha", 0.5))) if result else 0.5
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
    k_col2.metric("Left Wheel Speed (ω_L)", f"{w_l:.2f} rad/s")
    k_col3.metric("Right Wheel Speed (ω_R)", f"{w_r:.2f} rad/s")

# ==============================================================================
# TAB 3: TAVILY ADA COMPLIANCE PANEL
# ==============================================================================
with tab_tavily:
    st.subheader("📋 Tavily ADA Compliance Panel & Standards Catalog")
    st.markdown("Ground-truth accessibility standards retrieved for real-time spatial arbitration:")

    t_col1, t_col2 = st.columns([2.5, 1.0])
    with t_col1:
        query_input = st.text_input(
            "Search Accessibility Building Codes:",
            value="ADA doorway width standards",
            help="Queries Tavily API for live regulation specifications"
        )
    with t_col2:
        st.write("")
        st.write("")
        if st.button("🔍 Search Standards", type="primary", use_container_width=True):
            st.session_state["cached_standards"] = fetch_accessibility_context(query_input)
            st.success("Retrieved live accessibility context!")

    st.markdown("### 🏛️ Ground-Truth Accessibility Standards:")
    specs = get_standard_specs()
    sp_col1, sp_col2 = st.columns(2)
    with sp_col1:
        st.info(f"""
        **Doorway Clearance Standard:**
        - Code: `{specs['doorway']['standard_code']}`
        - Min Width: **{specs['doorway']['min_width_meters']} m** (32 inches)
        - Guideline: {specs['doorway']['guideline']}
        """)
    with sp_col2:
        st.info(f"""
        **Accessible Corridor Standard:**
        - Code: `{specs['corridor']['standard_code']}`
        - Min Width: **{specs['corridor']['min_width_meters']} m** (36 inches)
        - Guideline: {specs['corridor']['guideline']}
        """)

    st.markdown("### 📄 Active Context Summary Fed to AI:")
    st.code(str(st.session_state.get("cached_standards", "")))

# ==============================================================================
# TAB 4: LIVE NEBIUS AI JSON & API TELEMETRY
# ==============================================================================
with tab_api:
    st.subheader("⚡ Live Nebius AI JSON Inference Log Viewer")
    st.markdown("Raw real-time telemetry and spatial copilot inference payloads:")

    if result:
        st.json(result)
    else:
        st.info("No inference payload generated yet.")

# ==============================================================================
# TAB 5: CLOSED-LOOP DOORWAY RUN
# ==============================================================================
with tab_closed:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from closed_loop_tab import render_closed_loop
    render_closed_loop(default_drift=manual_steering_deg, default_speed=speed_input)
