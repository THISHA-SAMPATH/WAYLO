"""
WAYLO Guided Launcher
---------------------
Wraps the existing dashboard (simulation_streamlit/app.py) WITHOUT modifying it.
Adds exactly one thing: an interactive "How WAYLO works" walkthrough that opens
automatically on first visit and can be reopened from one sidebar button.

Run:  streamlit run simulation_streamlit/guided_app.py
"""

import math
import os
import runpy

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
ORIGINAL_APP = os.path.join(HERE, "app.py")

# The original app calls st.set_page_config(); only one call is allowed per run,
# so we make that call ourselves first and neutralise the second one.
st.set_page_config(
    page_title="WAYLO | Shared-Autonomy Mobility Copilot",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.set_page_config = lambda *a, **k: None

# --- Visual polish only (no new elements): CSS theme + crisper Matplotlib charts ---
with open(os.path.join(HERE, "theme.css"), encoding="utf-8") as _css:
    st.markdown(f"<style>{_css.read()}</style>", unsafe_allow_html=True)

plt.rcParams.update({
    "figure.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
    "grid.linewidth": 0.6,
    "legend.fancybox": True,
    "legend.framealpha": 0.9,
    "font.size": 9.5,
    "lines.solid_capstyle": "round",
})

TOTAL_STEPS = 5

if "tour_step" not in st.session_state:
    st.session_state["tour_step"] = 0
if "tour_seen" not in st.session_state:
    st.session_state["tour_seen"] = False


def _alpha_demo():
    """Tiny interactive demo: drag alpha and watch the blended path change."""
    drift, correction, v, L, r = 14.0, -14.0, 0.85, 0.60, 0.16
    alpha = st.slider(
        "Copilot authority α  (0 = you drive, 1 = copilot drives)",
        0.0, 1.0, 0.45, 0.05, key="tour_alpha",
    )
    blended = drift + alpha * correction
    omega = (v / L) * math.tan(math.radians(blended))
    w_l = (v - omega * L / 2) / r
    w_r = (v + omega * L / 2) / r

    fig, ax = plt.subplots(figsize=(4.6, 2.9), facecolor="#0b0f19")
    ax.set_facecolor("#111827")
    ax.set_xlim(-2.2, 2.2)
    ax.set_ylim(0, 4.6)
    ax.axhline(3.6, xmin=0.0, xmax=0.34, color="#475569", lw=6)
    ax.axhline(3.6, xmin=0.66, xmax=1.0, color="#475569", lw=6)
    ax.plot([-0.7, 0.7], [3.6, 3.6], "--", color="#22c55e", lw=2)
    for ang, col, lw in [(drift, "#f43f5e", 2.5), (blended, "#22c55e", 3.2)]:
        rad = np.radians(90 - ang)
        ax.annotate("", xy=(3.2 * np.cos(rad), 0.5 + 3.2 * np.sin(rad)), xytext=(0, 0.5),
                    arrowprops=dict(arrowstyle="->", color=col, lw=lw))
    ax.plot(0, 0.5, "s", color="#2563eb", ms=12)
    ax.text(-2.1, 4.3, "red = your drift   green = WAYLO blend", color="#94a3b8", fontsize=8)
    ax.tick_params(colors="#64748b", labelsize=7)
    for s in ax.spines.values():
        s.set_color("#374151")
    st.pyplot(fig)
    plt.close(fig)
    st.caption(
        f"Blended steering **{blended:+.1f}°** · left wheel **{w_l:.2f}** rad/s · "
        f"right wheel **{w_r:.2f}** rad/s"
    )


STEPS = [
    ("♿ What is WAYLO?", lambda: st.markdown(
        "WAYLO is a **copilot for electric wheelchairs**. When a driver's hand drifts "
        "(tremor, fatigue, spasm), WAYLO nudges the chair back toward a safe path "
        "through narrow doorways, corridors and docking spots.\n\n"
        "It never takes the stick away. It **blends** your input with its own correction, "
        "and only hits the brakes when an obstacle is truly close."
    )),
    ("🕹️ Step 1: Drive from the sidebar", lambda: st.markdown(
        "On the left you will find everything you need:\n\n"
        "- **Target Indoor Scenario**: Doorway, Corridor, Table or Emergency Stop.\n"
        "- **Manual Steering Drift Angle**: how far your joystick hand is drifting.\n"
        "- **Target Linear Velocity**: how fast you want to go.\n\n"
        "With *Real-Time Spatial Copilot Assist* ticked, the result updates as you move a "
        "slider. Otherwise press **⚡ Run Spatial Inference**."
    )),
    ("📡 Step 2: Read the cockpit", lambda: st.markdown(
        "In the **Shared-Autonomy Cockpit** tab:\n\n"
        "- 🔴 **Red arrow**: where the chair would go with no help.\n"
        "- 🟢 **Green dashed arrow**: where WAYLO steers it instead.\n"
        "- **Left / Right Clearance**: free space on each side, in metres.\n"
        "- **Authority α**: how much the copilot is helping right now.\n"
        "- **Banner colour**: green = nominal, yellow = centering, red = emergency brake."
    )),
    ("🎛️ Step 3: Try the blend yourself", lambda: (
        st.markdown(
            "This is the heart of WAYLO. Drag α and watch the green path rotate "
            "away from your drift toward the centre of the door."
        ),
        _alpha_demo(),
    )),
    ("🌐 Step 4: Online or offline", lambda: st.markdown(
        "**No setup needed.** Without API keys WAYLO uses a built-in physics engine.\n\n"
        "Optionally add keys in `.env`:\n\n"
        "- **Nebius**: live NVIDIA Nemotron reasoning (status shows 🟢 in the sidebar).\n"
        "- **Tavily**: live ADA / ISO 7176 accessibility standards (🌐 tab).\n\n"
        "The other tabs show the wheel-speed maths and the raw API payload. "
        "Reopen this guide any time with **❓ How it works**."
    )),
]


def _go(delta):
    st.session_state["tour_step"] += delta


def _tour_body():
    step = st.session_state["tour_step"]
    title, render = STEPS[step]
    st.progress((step + 1) / TOTAL_STEPS, text=f"Step {step + 1} of {TOTAL_STEPS}")
    st.subheader(title)
    render()

    back, _, nxt = st.columns([1, 2, 1])
    last = step == TOTAL_STEPS - 1
    if step > 0:
        back.button("◀ Back", key="tour_back", use_container_width=True, on_click=_go, args=(-1,))
    clicked = nxt.button("Start driving ✓" if last else "Next ▶", key="tour_finish" if last else "tour_next",
                         type="primary", use_container_width=True,
                         on_click=None if last else _go, args=None if last else (1,))
    if last and clicked:
        st.session_state["tour_seen"] = True
        st.session_state["tour_step"] = 0
        st.rerun()  # full rerun closes the dialog


_HAS_DIALOG = hasattr(st, "dialog")
if _HAS_DIALOG:
    tour = st.dialog("How WAYLO works", width="large")(_tour_body)
else:  # older Streamlit: fall back to an expander at the top of the page
    def tour():
        with st.expander("How WAYLO works", expanded=True):
            _tour_body()

# One extra sidebar element: the button to reopen the guide.
reopen = st.sidebar.button("❓ How it works", use_container_width=True)
if reopen:
    st.session_state["tour_seen"] = False
    st.session_state["tour_step"] = 0

if not st.session_state["tour_seen"]:
    tour()

# Run the untouched original dashboard.
runpy.run_path(ORIGINAL_APP, run_name="__main__")
