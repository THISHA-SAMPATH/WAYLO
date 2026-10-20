import sys
import os
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from matplotlib.lines import Line2D
import streamlit as st

# Ensure repository root is on sys.path for backend imports
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from backend.nebius_client import analyze_spatial_frame, get_api_key
from backend.tavily_search import fetch_accessibility_context

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="WAYLO: Autonomous Mobility Copilot",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0px;
        background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-card {
        background-color: #1e293b;
        padding: 12px 16px;
        border-radius: 8px;
        border: 1px solid #334155;
        margin-bottom: 8px;
    }
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">♿ WAYLO: YOUR WORLD. YOUR WAY.</h1>', unsafe_allow_html=True)
st.caption("AI-Powered Shared-Autonomy Mobility Copilot | NVIDIA Nemotron/Cosmos on Nebius AI Cloud")

# --- Session State Initialization ---
if "inference_result" not in st.session_state:
    st.session_state["inference_result"] = None
if "last_scenario" not in st.session_state:
    st.session_state["last_scenario"] = None
if "cached_accessibility" not in st.session_state:
    st.session_state["cached_accessibility"] = fetch_accessibility_context()

# --- Sidebar Controls ---
st.sidebar.header("🕹️ Vehicle & Intent Controls")

# API Configuration Expander
with st.sidebar.expander("☁️ Nebius AI Cloud Settings", expanded=False):
    default_env_key = os.getenv("NEBIUS_API_KEY", "")
    api_key_input = st.text_input(
        "Nebius API Key:",
        value=default_env_key if default_env_key != "your_nebius_api_key_here" else "",
        type="password",
        help="Leave blank to run in offline local simulation mode"
    )
    base_url_input = st.text_input(
        "Base URL:",
        value=os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1")
    )
    model_choice = st.selectbox(
        "Nebius Model:",
        ["nvidia/nemotron-3-ultra", "nvidia/cosmos-nemotron-34b", "meta-llama/Llama-3.3-70B-Instruct"]
    )

with st.sidebar.expander("🌐 Tavily Accessibility Search", expanded=False):
    tavily_query = st.text_input(
        "Accessibility Query:",
        value="ADA wheelchair doorway minimum clearance",
        help="Search live accessibility regulations & spatial metrics via Tavily"
    )
    if st.button("🔍 Search Standards", use_container_width=True):
        with st.spinner("Fetching live accessibility context..."):
            st.session_state["cached_accessibility"] = fetch_accessibility_context(tavily_query)
            st.rerun()

# Connection Status Badge
active_key = get_api_key(api_key_input)
if active_key:
    st.sidebar.success("🟢 Nebius Cloud: Connected")
else:
    st.sidebar.info("🟡 Copilot Mode: Local Simulation")

user_intent = st.sidebar.selectbox(
    "Select Target Intent:",
    ["Align with Doorway", "Navigate Tight Corridor", "Dock at Table", "Emergency Stop Test"]
)

manual_steering_deg = st.sidebar.slider("Manual Steering Input (Angle °):", -45, 45, 0, step=1)
speed_input = st.sidebar.slider("Target Velocity (m/s):", 0.0, 2.0, 0.8, step=0.1)

auto_recalculate = st.sidebar.checkbox("Real-time Copilot Assist", value=True, help="Automatically recalculates spatial trajectory corrections when sliders change")
trigger_inference = st.sidebar.button("⚡ Run Nebius Spatial Inference", type="primary", use_container_width=True)

# Helper function to execute inference
def run_copilot_inference():
    metadata = {
        "scenario": user_intent,
        "steering_angle": manual_steering_deg,
        "speed": speed_input,
        "timestamp": "2026-10-20T12:00:00Z"
    }
    return analyze_spatial_frame(
        image_payload=json.dumps(metadata),
        user_intent=user_intent,
        steering_deg=float(manual_steering_deg),
        speed_mps=float(speed_input),
        api_key=api_key_input if active_key else None,
        base_url=base_url_input,
        model=model_choice,
        accessibility_context=st.session_state.get("cached_accessibility")
    )

# Trigger logic: either explicit button or real-time change
should_infer = trigger_inference or (auto_recalculate and (
    st.session_state["inference_result"] is None or
    st.session_state["last_scenario"] != (user_intent, manual_steering_deg, speed_input)
))

if should_infer:
    with st.spinner("Processing spatial vision frame via Nebius AI Cloud..."):
        st.session_state["inference_result"] = run_copilot_inference()
        st.session_state["last_scenario"] = (user_intent, manual_steering_deg, speed_input)

result = st.session_state.get("inference_result")

# --- Layout: 2 Columns ---
col1, col2 = st.columns([1.8, 1.2])

with col1:
    st.subheader("🗺️ 2D Indoor Spatial Room Grid & Trajectory")

    # Generate 2D Room Plot with dark-mode aesthetic
    fig, ax = plt.subplots(figsize=(7, 5), facecolor="#0e1117")
    ax.set_facecolor("#161b22")
    ax.set_xlim(-3, 3)
    ax.set_ylim(0, 6)

    # Wheelchair Base Coordinate
    chair_x, chair_y = 0.0, 1.0

    # Draw Wheelchair Chassis
    chassis = Rectangle((chair_x - 0.25, chair_y - 0.25), 0.5, 0.5, color="#2563eb", zorder=4)
    ax.add_patch(chassis)
    ax.plot(chair_x, chair_y, "o", color="#60a5fa", markersize=8, zorder=5)

    # Scenario-specific environmental obstacles
    if user_intent == "Align with Doorway":
        # Left and Right walls creating a 1.4m central doorway at Y=4.5m
        ax.add_patch(Rectangle((-2.8, 4.5), 2.1, 0.3, color="#64748b", zorder=3))
        ax.add_patch(Rectangle((0.7, 4.5), 2.1, 0.3, color="#64748b", zorder=3))
        ax.plot([-0.7, 0.7], [4.5, 4.5], "--", color="#22c55e", linewidth=2.5, zorder=3)
        ax.text(0.0, 4.8, "Doorway Target (1.4m)", color="#86efac", ha="center", fontsize=9, fontweight="bold")

    elif user_intent == "Navigate Tight Corridor":
        # Walls bounding a narrow corridor 1.2m wide from Y=2.0m to Y=5.5m
        ax.add_patch(Rectangle((-2.8, 2.0), 2.2, 3.5, color="#64748b", zorder=3))
        ax.add_patch(Rectangle((0.6, 2.0), 2.2, 3.5, color="#64748b", zorder=3))
        ax.plot([0.0, 0.0], [2.0, 5.5], ":", color="#38bdf8", linewidth=1.5, zorder=2)
        ax.text(0.0, 5.65, "Corridor Centerline", color="#7dd3fc", ha="center", fontsize=9)

    elif user_intent == "Dock at Table":
        # Table obstacle at Y=3.8m with docking slot
        ax.add_patch(Rectangle((-1.4, 3.8), 2.8, 1.4, color="#a855f7", alpha=0.8, zorder=3))
        ax.plot([-0.5, 0.5], [3.8, 3.8], "--", color="#fbbf24", linewidth=2.5, zorder=4)
        ax.text(0.0, 4.4, "Workstation / Table", color="#f3e8ff", ha="center", fontsize=10, fontweight="bold")
        ax.text(0.0, 3.55, "Docking Bay", color="#fde047", ha="center", fontsize=9)

    elif user_intent == "Emergency Stop Test":
        # Open room with unexpected dynamic hazard at Y=2.5m
        ax.add_patch(Rectangle((-2.8, 5.0), 5.6, 0.3, color="#64748b", zorder=3))
        hazard_circle = Circle((0.0, 2.5), 0.35, color="#ef4444", zorder=5)
        safety_perimeter = Circle((0.0, 2.5), 0.85, fill=False, edgecolor="#f87171", linestyle="--", linewidth=1.5, zorder=3)
        ax.add_patch(hazard_circle)
        ax.add_patch(safety_perimeter)
        ax.text(0.0, 2.5, "⚠️", color="white", ha="center", va="center", fontsize=12)
        ax.text(0.0, 3.0, "Dynamic Obstacle", color="#fca5a5", ha="center", fontsize=9, fontweight="bold")

    # Draw Manual User Trajectory Vector (Red)
    rad_user = np.radians(90 - manual_steering_deg)
    len_user = 1.8
    dx_user = np.cos(rad_user) * len_user
    dy_user = np.sin(rad_user) * len_user
    ax.annotate(
        "", xy=(chair_x + dx_user, chair_y + dy_user), xytext=(chair_x, chair_y),
        arrowprops=dict(arrowstyle="->,head_width=0.4,head_length=0.6", color="#f43f5e", lw=2.5),
        zorder=6
    )

    # Draw WAYLO Corrected Vector if inference is active
    if result:
        is_emergency = result.get("emergency_stop", False)
        if is_emergency:
            # Emergency Stop Indicator
            ax.plot(chair_x, chair_y + 0.5, "x", color="#ef4444", markersize=14, markeredgewidth=3.5, zorder=7)
            ax.text(chair_x, chair_y + 0.7, "BRAKE HALT", color="#ef4444", ha="center", fontsize=9, fontweight="bold")
        else:
            # Calculate corrected trajectory
            correction_deg = float(result.get("steering_correction_deg", 0.0))
            corrected_angle = (90 - manual_steering_deg) + correction_deg
            rad_corr = np.radians(corrected_angle)
            len_corr = 3.2
            dx_corr = np.cos(rad_corr) * len_corr
            dy_corr = np.sin(rad_corr) * len_corr
            ax.annotate(
                "", xy=(chair_x + dx_corr, chair_y + dy_corr), xytext=(chair_x, chair_y),
                arrowprops=dict(arrowstyle="->,head_width=0.45,head_length=0.7", color="#22c55e", lw=3.0, linestyle="--"),
                zorder=7
            )

    # Legend with clean proxy Line2D handles to avoid matplotlib FancyArrow warnings
    legend_handles = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#2563eb", markersize=10, label="WAYLO Wheelchair"),
        Line2D([0], [0], color="#f43f5e", lw=2.5, label="User Steering Input"),
        Line2D([0], [0], color="#22c55e", lw=3.0, linestyle="--", label="WAYLO Copilot Correction"),
        Line2D([0], [0], color="#64748b", lw=6, label="Room Boundaries / Walls"),
    ]
    ax.legend(handles=legend_handles, loc="lower right", facecolor="#1e293b", edgecolor="#334155", labelcolor="white", fontsize=8.5)

    ax.grid(True, linestyle=":", alpha=0.3, color="#94a3b8")
    ax.tick_params(colors="#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#334155")
    ax.set_xlabel("Lateral X Distance (meters)", color="#94a3b8", fontsize=9)
    ax.set_ylabel("Forward Y Distance (meters)", color="#94a3b8", fontsize=9)

    st.pyplot(fig)
    plt.close(fig)

with col2:
    st.subheader("📡 Spatial Sensor Telemetry")

    if result:
        clearance_l = result.get("clearance_left", 0.40)
        clearance_r = result.get("clearance_right", 0.40)
        risk_score = result.get("hazard_risk_score", 10)
        is_emergency = result.get("emergency_stop", False)
        rec_vel = result.get("recommended_velocity", f"{speed_input} m/s")
        correction = result.get("steering_correction_deg", 0.0)

        # Telemetry metrics row
        m1, m2 = st.columns(2)
        m1.metric("Left Clearance", f"{clearance_l:.2f} m", delta=f"{clearance_l - 0.40:+.2f} m")
        m2.metric("Right Clearance", f"{clearance_r:.2f} m", delta=f"{clearance_r - 0.40:+.2f} m")

        m3, m4 = st.columns(2)
        risk_delta = f"{risk_score - 20:+d}%"
        m3.metric("Hazard Risk", f"{risk_score}%", delta=risk_delta, delta_color="inverse")
        m4.metric("Copilot Velocity", rec_vel, delta=result.get("speed_buffer_override", "NOMINAL"))

        # Dynamic Status Banner
        if is_emergency:
            st.error("🚨 **EMERGENCY STOP TRIGGERED**: Dynamic obstacle inside wheelchair stopping zone. Motors disengaged.")
        elif abs(correction) > 2.0:
            st.warning(f"🔄 **SHARED-AUTONOMY INTERVENTION**: Applying **{correction:+.1f}°** steering adjustment.")
        else:
            st.success("✅ **TRAJECTORY NOMINAL**: Clearance is clear. Minimal copilot intervention.")

        st.divider()
        st.subheader("🧠 Nebius AI Inference Log")

        # Source and Model badges
        source_label = "🟢 Nebius AI Cloud (Live)" if "nebius_cloud" in result.get("source", "") else "🟡 Local Simulation Engine"
        st.caption(f"**Inference Source:** {source_label} | **Model:** `{result.get('model', 'nvidia/nemotron-3-ultra')}`")

        # Spatial summary explanation
        st.info(f"**Copilot Advisory:**\n\n{result.get('spatial_summary', '')}")

        # Accessibility Context
        if result.get("accessibility_context"):
            with st.expander("🌐 Accessibility Standards & Context (Tavily)", expanded=False):
                st.markdown(f"**Retrieved Standards:**\n\n{result['accessibility_context']}")

        # Expandable JSON response
        with st.expander("🔍 View Raw Spatial Inference Payload", expanded=False):
            st.json(result)

    else:
        st.info("Click '⚡ Run Nebius Spatial Inference' or move the steering controls to view copilot feedback.")

st.divider()
st.markdown("""
### 🛡️ Shared Autonomy Blending Model
$$v_{\\text{final}} = (1 - \\alpha) v_{\\text{user}} + \\alpha v_{\\text{copilot}}$$
WAYLO continuously blends user intent with real-time NVIDIA Nemotron / Cosmos spatial awareness on Nebius AI Cloud. When clearance thresholds tighten or obstacles enter the stopping perimeter, the copilot seamlessly scales $\\alpha \\to 1.0$ to ensure user safety and collision avoidance.
""")