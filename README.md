# ♿ WAYLO — YOUR WORLD. YOUR WAY.
> **Physical AI Shared-Autonomy Spatial Copilot for Electric Wheelchairs**  
> *Submitted to the NVIDIA x Nebius Global AI Hackathon — Physical AI Track*  
> Powered by **NVIDIA Nemotron** on **Nebius Token Factory** & **Tavily Search API**

[![Track: Physical AI](https://img.shields.io/badge/Track-Physical_AI-76B900?logo=nvidia&logoColor=white)](https://devpost.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Nebius AI Cloud](https://img.shields.io/badge/Nebius_AI-Token_Factory-00D4FF?logo=cloud&logoColor=white)](https://tokenfactory.nebius.com)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron-76B900?logo=nvidia&logoColor=white)](https://tokenfactory.nebius.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](http://localhost:8000/docs)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![MATLAB 3D Kinematics](https://img.shields.io/badge/MATLAB-3D_Kinematics-ED8B00?logo=mathworks&logoColor=white)](https://mathworks.com)
[![Tavily Search](https://img.shields.io/badge/Tavily-Regional_Accessibility_Standards-4F46E5)](https://tavily.com)

---

> [!NOTE]
> **SIMULATION RESEARCH DISCLAIMER**: All performance benchmarks, collision statistics, pass rates, and kinematics reported in this repository are evaluated in simulated physical environments (closed-loop Runge-Kutta 4th-order ODE kinematics and simulated 2D LiDAR ray-casting in parameterized doorway scenarios). These results represent robotic software simulation benchmarks, not physical clinical road trials with human patients.

---

## 📋 Executive Summary & Architecture Overview

| Parameter | Details |
| :--- | :--- |
| **Hackathon Track** | **Physical AI** (Robotic Kinematics, Shared Autonomy, Spatial Perception) |
| **Frontier Models** | NVIDIA **Nemotron-3-Ultra** (`nvidia/nemotron-3-ultra`) on Nebius Token Factory |
| **Local Real-Time Loop** | 50 Hz deterministic perception, alpha blending, unicycle kinematics (no cloud calls) |
| **Cloud Reasoning (Async)** | Natural language voice command compilation & caregiver incident narration on Nebius |
| **Accessibility Search** | **Tavily Search API** with regional jurisdiction standards (US/ADA, UK, EU, AU, CA) |
| **Kinematic Model** | Differential-drive unicycle ($L=0.60\,\text{m}, r=0.16\,\text{m}$), 4th-Order Runge-Kutta ODE solvers |
| **Privacy Pipeline** | Real depth-only aperture extractor (RGB dropped immediately; 0 images written; 0 frames sent to cloud) |
| **Clinical Ledger** | Event tracking (`near_miss`, `scrape`, `collision`), independence metrics, and modeled repair costs |
| **Software Stack** | Python (FastAPI, NumPy, Pillow, Pytest), Streamlit cockpit dashboard, MATLAB 3D physical world |
| **License** | [MIT License](LICENSE) |

---

## 🏛️ 1. Local Control Loop vs. Nebius Cloud Architecture

To guarantee deterministic safety and real-time responsiveness (<20ms latency), WAYLO strictly decouples the sub-50ms steering control loop from cloud inference.

```text
====================================================================================================
                        LOCAL REAL-TIME CONTROL LOOP (Runs at 50 Hz on Chair Compute)
====================================================================================================

      +------------------------+
      |  HUMAN DRIVER JOYSTICK |
      |  - manual steering     |
      |  - speed input         |
      +-----------+------------+
                  |
                  | phi_user, v_user
                  v
      +------------------------+       LiDAR / Depth        +-------------------------------+
      |    SHARED AUTONOMY     | <------------------------- | LOCAL GEOMETRIC PERCEPTION    |
      |    ARBITRATION LAYER   |                            | - 2D LiDAR Scan (backend)     |
      | alpha = clip(risk, 0,1)|                            | - Depth Aperture (privacy)    |
      | phi = (1-a)u + a cop   |                            | - Autonomous Emergency Brake  |
      +-----------+------------+                            +-------------------------------+
                  |
                  v
      +------------------------+
      | DIFFERENTIAL UNICYCLE  |
      | KINEMATIC ACTUATION    |
      | - left/right wheel rad |
      +------------------------+

====================================================================================================
               NEBIUS TOKEN FACTORY (NVIDIA NEMOTRON) - Asynchronous Non-Control Tasks
====================================================================================================

  [User Spoken Audio] ----> compile_voice_command(text) ----> NVIDIA Nemotron on Nebius Token Factory
                                                                 |
                                                                 v
                                                 Bounded JSON (Speed Cap: 0.2-1.0 m/s,
                                                 Clearance Margin: 0.05-0.50m, Mode)
                                                                 |
                                                                 v
                                            [Deterministic Safety Layer: Final Authority]

  [Sanitized Telemetry] --> narrate_incident(event) --------> NVIDIA Nemotron on Nebius Token Factory
  (No images/points)                                             |
                                                                 v
                                                 1-2 Sentence Plain-English Caregiver Summary
                                                 (Logged to API Audit List with Model & Latency)
```

### Exact Breakdown: What Runs Locally vs. On Nebius

| Component | Execution Location | Latency | Cloud Dependency | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Perception & Gap Detection** | **Local (Wheelchair CPU)** | ~2 ms | **None (Never calls cloud)** | Real-time LiDAR raycasting and doorway detection |
| **Real Depth-Only Privacy Filter**| **Local (Wheelchair CPU)** | ~5 ms | **None (Never calls cloud)** | Extracts 4 scalar doorway features; drops RGB immediately |
| **Arbitration Blending ($\alpha$)** | **Local (Wheelchair CPU)** | <1 ms | **None (Never calls cloud)** | Proportional blending between human and copilot |
| **Emergency Braking (AEB)** | **Local (Wheelchair CPU)** | <1 ms | **None (Never calls cloud)** | Stopping distance safety override |
| **Voice Command Compiler** | **Nebius Token Factory** | ~400-800 ms | NVIDIA Nemotron | Compiles natural language into bounded control parameters |
| **Incident Narrator** | **Nebius Token Factory** | ~500-900 ms | NVIDIA Nemotron | Generates plain-English caregiver incident summaries |
| **Regional Standards Search** | **Tavily Search API** | ~600 ms | Tavily Search | Dynamically fetches regional accessibility building codes |

---

## 🔒 2. Real Depth-Only Local Privacy Pipeline

Rather than relying on vague "zero leakage" claims, WAYLO defines and tests explicit code-level privacy guarantees in `backend/privacy_scrubber.py`:

1. **Immediate In-Memory RGB Discard**: If an optional RGB frame is passed to the pipeline, the reference is deleted immediately from memory (`del rgb_image`) upon entry. RGB data is never stored, logged, or serialized.
2. **Local Geometric Dimensionality Reduction**: Metric depth frames ($H \times W$ float meters from `.npy` arrays or 16-bit PNG depth images) are processed locally by geometric scanline aperture detection.
3. **Strict Scalar Output**: Only 4 scalar doorway features leave the module:
   - Doorway width ($m$)
   - Lateral offset ($m$)
   - Approach angle ($^\circ$)
   - Distance to door plane ($m$)
   *No image arrays, raw point clouds, or pixel grids ever leave this module.*
4. **Verified Audit Invariants**:
   - `images_written == 0` (strictly 0 files written to disk)
   - `depth_frames_sent_to_cloud == 0` (strictly 0 depth frames transmitted over network)
   - `rgb_discarded` increments whenever an RGB buffer is provided

Test verification is available via `tests/test_privacy_pipeline.py` and the CLI demonstration script:
```bash
python scripts/run_on_depth_image.py
```

---

## 📊 3. Honest Human Baseline & Reproducible Monte Carlo Evaluation

### The Three Experimental Conditions
Prior naive simulations assumed drivers hold an uncorrected constant steering error. In real life, wheelchair operators actively attempt to correct their path, but are constrained by sensory latency and neuromotor impairments. WAYLO evaluates three distinct conditions:

1. **Uncorrected**: Open-loop driver maintaining a constant drift bias plus hand tremor.
2. **Corrective**: Closed-loop human driver model incorporating:
   - Visual-motor reaction delay ($\tau \in [0.2, 0.6]\,\text{s}$)
   - Visual-feedback gain aiming at doorway center
   - Physiological/pathological hand tremor ($4.5\,\text{Hz}$)
   - Sensor / joystick noise
   - Neuromuscular fatigue term that increases heading drift error over time
3. **WAYLO**: The same corrective human driver supported by WAYLO's local shared-autonomy copilot.

### Reproducible Monte Carlo Benchmark Table
Below are the empirical simulation results across 100 randomized trials (`--n 100`, `--seed 42`) across 5 doorway widths $\{0.81\,\text{m}, 0.91\,\text{m}, 1.0\,\text{m}, 1.1\,\text{m}, 1.4\,\text{m}\}$, reporting 95% Wilson confidence intervals:

| Door Width ($m$) | Condition | Collision Rate (95% Wilson CI) | Pass Rate (95% Wilson CI) | Mean Clearance ($m$) |
| :--- | :--- | :--- | :--- | :--- |
| **0.81 m** (Tight ADA) | Uncorrected | **100.0%** [79.6%, 100.0%] | 0.0% [0.0%, 20.4%] | -0.393 m |
| | Corrective | **100.0%** [79.6%, 100.0%] | 0.0% [0.0%, 20.4%] | -0.244 m |
| | **WAYLO** | **0.0%** [0.0%, 20.4%] | **100.0%** [79.6%, 100.0%] | **+0.013 m** |
| **0.91 m** (Standard ADA) | Uncorrected | **90.3%** [75.1%, 96.7%] | 9.7% [3.4%, 24.9%] | -0.330 m |
| | Corrective | **80.7%** [63.7%, 90.8%] | 19.4% [9.2%, 36.3%] | -0.170 m |
| | **WAYLO** | **0.0%** [0.0%, 11.0%] | **100.0%** [89.0%, 100.0%] | **+0.050 m** |
| **1.00 m** (Commercial) | Uncorrected | **94.1%** [73.0%, 99.0%] | 5.9% [1.1%, 27.0%] | -0.414 m |
| | Corrective | **82.3%** [59.0%, 93.8%] | 17.6% [6.2%, 41.0%] | -0.191 m |
| | **WAYLO** | **0.0%** [0.0%, 18.4%] | **100.0%** [81.6%, 100.0%] | **+0.068 m** |
| **1.10 m** (Wide Corridor) | Uncorrected | **70.6%** [46.9%, 86.7%] | 29.4% [13.3%, 53.1%] | -0.239 m |
| | Corrective | **47.1%** [26.2%, 69.0%] | 52.9% [31.0%, 73.8%] | -0.043 m |
| | **WAYLO** | **0.0%** [0.0%, 18.4%] | **100.0%** [81.6%, 100.0%] | **+0.141 m** |
| **1.40 m** (Double Door) | Uncorrected | **65.0%** [43.3%, 81.9%] | 35.0% [18.1%, 56.7%] | -0.072 m |
| | Corrective | **20.0%** [8.1%, 41.6%] | 80.0% [58.4%, 91.9%] | +0.166 m |
| | **WAYLO** | **0.0%** [0.0%, 16.1%] | **100.0%** [83.9%, 100.0%] | **+0.297 m** |
| **OVERALL** | Uncorrected | **84.0%** [75.6%, 89.9%] | 16.0% [10.1%, 24.4%] | -0.287 m |
| | Corrective | **66.0%** [56.3%, 74.5%] | 34.0% [25.5%, 43.7%] | -0.096 m |
| | **WAYLO** | **0.0%** [0.0%, 3.7%] | **100.0%** [96.3%, 100.0%] | **+0.112 m** |

### Reproducing the Simulation
Run the automated Monte Carlo CLI script:
```bash
python scripts/monte_carlo.py --n 100 --seed 42 --out data/monte_carlo
```
Outputs `runs.csv` and `summary.json`.

### Physical Limitations & Failure Modes
In stress testing with severe parameters (e.g. drift $> 25^\circ$, approach speeds $> 1.0\,\text{m/s}$ in $0.81\,\text{m}$ doorways), physical limits of chassis yaw acceleration ($\omega_{\max} = 1.2\,\text{rad/s}$) and stopping distance can lead to AEB halts before the doorway or minor scrapes. WAYLO explicitly documents these kinematic bounds rather than claiming impossible 100% universal avoidance under all physical dynamics.

---

## 📈 4. Clinical & Economic Mobility Ledger

Implemented in `backend/ledger.py` and exposed via `/api/v1/ledger/*`:

### Tracked Events
- `assist_engaged`: Copilot smoothly assumes guidance authority ($\alpha \ge 0.10$).
- `near_miss`: Proximity falls below safety buffer (clearance $< 0.15\,\text{m}$) without contact.
- `scrape`: Physical brush with door boundary (clearance $< 0.04\,\text{m}$).
- `collision`: Impact with door jamb or wall boundary.
- `human_rescue`: Driver takes back manual joystick authority.

### Cumulative Metrics
- **Independence Ratio**: Proportion of navigation time driven without copilot takeover.
- **Assisted Time**: Cumulative duration (seconds) under shared guidance.
- **Corrections Saved**: Automated interventions that averted collisions or boundary scrapes.
- **Estimated Repair Cost Avoided**: Modeled facility maintenance and hardware servicing costs avoided, based on configurable operational assumptions:
  > *Disclaimer: Labeled as Model Assumptions. Repair cost estimates ($150 scrape, $850 collision repair) represent configurable operational heuristics derived from facility maintenance and wheelchair hardware servicing records.*

---

## 🔄 5. What We Significantly Updated After Aug 26

Based on the Git commit history and technical evolution:

* **Decoupled Nemotron from the Real-Time Control Loop** (`feat(nebius)`): Removed LLM inference from sub-50ms steering commands. Shifted NVIDIA Nemotron to asynchronous voice command compilation, caregiver incident narration, and full API audit logging.
* **Honest Corrective Human Baseline** (`feat(sim)`): Introduced a closed-loop human driver model featuring visual reaction delays (0.2–0.6s), visual-feedback gain, hand tremors, joystick noise, and cumulative neuromuscular fatigue.
* **Reproducible Monte Carlo Suite with Wilson CIs** (`feat(eval)`): Built `scripts/monte_carlo.py` to evaluate 3 conditions across 5 doorway widths with rigorous 95% Wilson score confidence intervals and limitation logging.
* **Real Depth-Only Privacy Filter** (`feat(privacy)`): Replaced mock token generators with a real depth array and 16-bit PNG parser that immediately drops RGB in-memory and outputs only 4 scalar doorway features with verified audit counters (0 disk writes, 0 cloud frames).
* **Regional Standards Integration via Tavily** (`feat(standards)`): Added a regional parameter to Tavily search (US, UK, EU, AU, CA, GLOBAL) with automated regex width parsing and verified cached catalog fallbacks.
* **Mobility Safety & Independence Ledger** (`feat(ledger)`): Created an in-memory event logger and metric engine calculating user independence ratios, assisted duration, corrections saved, and modeled repair savings with labeled assumptions.
* **Codebase Pruning & Focus** (`chore(cleanup)`): Removed obsolete robot-arm modules and duplicate scripts (`docs/ggu`, `tests/bjh`, `simulation/app.py`), focusing the repository squarely on shared-autonomy mobility copilot navigation.

---

## ⚡ 6. Quick Start Guide

### Step 1: Environment Setup
```bash
git clone https://github.com/THISHA-SAMPATH/WAYLO.git
cd WAYLO
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy [.env.example](.env.example) to `.env`:
```bash
cp .env.example .env
```
Configure your credentials in `.env`:
```ini
NEBIUS_API_KEY=your_nebius_api_key_here
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
TAVILY_API_KEY=tvly-your_tavily_key_here
```
> *Note: If API keys are omitted or left as placeholders, WAYLO operates cleanly with verified deterministic fallbacks.*

### Step 3: Run the FastAPI Middleware Server
```bash
python backend/main.py
```
* Server runs at `http://localhost:8000`.
* Interactive OpenAPI Documentation: `http://localhost:8000/docs`.

### Step 4: Run the Dark-Mode Streamlit Dashboard
```bash
streamlit run simulation_streamlit/app.py
```
* Dashboard runs at `http://localhost:8501`.

### Step 5: Run Automated Verification Tests
```bash
python -m pytest -q
```
```text
67 passed in 4.56s
```

---

## 📄 License & Attribution
Distributed under the **MIT License**. See [LICENSE](LICENSE) for full details.  
Built for the **NVIDIA x Nebius Global AI Hackathon (Physical AI Track)**.
