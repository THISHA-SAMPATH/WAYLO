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
3. **WAYLO**: The same corrective human driver supported by WAYLO's local shared-autonomy copilot, subject to realistic sensor noise (Gaussian range noise $\sigma = 0.02\,\text{m}$, 2.0% random ray dropouts, and 0.10s sensor latency).

### Reproducible Monte Carlo Benchmark Table ($N=1000$, Seed=42)
Below are the empirical simulation results across 1000 randomized trials (`--n 1000`, `--seed 42`) across 5 doorway widths $\{0.81\,\text{m}, 0.91\,\text{m}, 1.0\,\text{m}, 1.1\,\text{m}, 1.4\,\text{m}\}$, speeds up to $1.20\,\text{m/s}$, and drift up to $\pm 25.0^\circ$, reporting 95% Wilson confidence intervals.  
*Note: In accordance with rigorous evaluation standards, minimum clearance is reported strictly for passed runs only, excluding negative collision clearances.*

| Door Width ($m$) | Condition | Collision Rate (95% Wilson CI) | Pass Rate (95% Wilson CI) | Min Clearance (Passed Runs Only) |
| :--- | :--- | :--- | :--- | :--- |
| **0.81 m** (Tight ADA, 32") | Uncorrected | **95.3%** [91.5%, 97.4%] | 4.7% [2.6%, 8.5%] | +0.037 m ($N=10$) |
| | Corrective | **86.7%** [81.5%, 90.7%] | 13.3% [9.3%, 18.5%] | +0.044 m ($N=28$) |
| | **WAYLO** | **12.8%** [9.0%, 18.0%] | **87.2%** [82.0%, 91.1%] | **+0.025 m** ($N=184$) |
| **0.91 m** (Standard ADA, 36") | Uncorrected | **93.2%** [88.9%, 95.9%] | 6.8% [4.1%, 11.1%] | +0.060 m ($N=14$) |
| | Corrective | **78.2%** [72.0%, 83.3%] | 21.8% [16.8%, 28.0%] | +0.060 m ($N=45$) |
| | **WAYLO** | **0.97%** [0.27%, 3.47%] | **99.0%** [96.5%, 99.7%] | **+0.048 m** ($N=204$) |
| **1.00 m** (Commercial) | Uncorrected | **84.7%** [79.1%, 89.0%] | 15.3% [11.0%, 20.9%] | +0.097 m ($N=31$) |
| | Corrective | **68.5%** [61.8%, 74.5%] | 31.5% [25.5%, 38.2%] | +0.102 m ($N=64$) |
| | **WAYLO** | **0.0%** [0.0%, 1.86%] | **100.0%** [98.1%, 100.0%] | **+0.082 m** ($N=203$) |
| **1.10 m** (Wide Corridor) | Uncorrected | **87.2%** [81.9%, 91.2%] | 12.8% [8.8%, 18.2%] | +0.097 m ($N=25$) |
| | Corrective | **63.3%** [56.3%, 69.7%] | 36.7% [30.3%, 43.7%] | +0.109 m ($N=72$) |
| | **WAYLO** | **0.0%** [0.0%, 1.92%] | **100.0%** [98.1%, 100.0%] | **+0.126 m** ($N=196$) |
| **1.40 m** (Double Door) | Uncorrected | **75.5%** [68.9%, 81.2%] | 24.5% [18.8%, 31.2%] | +0.163 m ($N=45$) |
| | Corrective | **31.0%** [24.7%, 38.0%] | 69.0% [62.0%, 75.3%] | +0.185 m ($N=127$) |
| | **WAYLO** | **0.0%** [0.0%, 2.05%] | **100.0%** [98.0%, 100.0%] | **+0.280 m** ($N=184$) |
| **OVERALL ($N=1000$)** | Uncorrected | **87.5%** [85.3%, 89.4%] | 12.5% [10.6%, 14.7%] | +0.112 m ($N=125$) |
| | Corrective | **66.4%** [63.4%, 69.3%] | 33.6% [30.7%, 36.6%] | +0.124 m ($N=336$) |
| | **WAYLO** | **2.9%** [2.03%, 4.13%] | **97.1%** [95.9%, 98.0%] | **+0.111 m** ($N=971$) |

### Physiological Sensitivity Sweep (`data/monte_carlo/sensitivity.csv`)
A systematic sensitivity analysis evaluated the impact of varying human driver impairment parameters across plausible clinical ranges:

| Parameter Swept | Values | Corrective Baseline Collision Rate | WAYLO Collision Rate | Key Empirical Finding |
| :--- | :--- | :--- | :--- | :--- |
| **Reaction Delay** ($\tau$) | 0.15s $\to$ 0.65s | 60.0% $\to$ 78.0% | **0.0% $\to$ 4.0%** | Higher delays impair visual steering correction; WAYLO prevents 95%+ of delayed collisions. |
| **Visual Aiming Gain** ($K_v$) | 0.6 $\to$ 1.8 | 94.0% $\to$ 36.0% | **4.0% $\to$ 0.0%** | Low visual tracking causes severe collisions; WAYLO restores pass rate to 96%+ even at $K_v=0.6$. |
| **Hand Tremor** | 0.5° $\to$ 4.5° | 50.0% $\to$ 72.0% | **0.0% $\to$ 2.0%** | High involuntary tremor destabilizes manual steering; WAYLO filtering eliminates 97% of tremor collisions. |
| **Fatigue Rate** | 0.01 $\to$ 0.10 | 56.0% $\to$ 82.0% | **0.0% $\to$ 8.0%** | Severe fatigue compounds drift over time; WAYLO maintains $\ge 92\%$ pass rate even under heavy fatigue. |

### Physical Limitations & Empirical Failure Case Analysis
Across 1000 randomized Monte Carlo trials, WAYLO experienced exactly **29 failures (2.9%)**:
- **Door Width Distribution**: 27 of 29 failures (93.1%) occurred on the narrowest $0.81\,\text{m}$ (32") doorways, where a $0.65\,\text{m}$ wheelchair has only $0.08\,\text{m}$ (8 cm) of total margin per side. 2 failures occurred on $0.91\,\text{m}$ doors under extreme drift ($> 24.5^\circ$) combined with long latency (0.60s). Zero failures occurred on doors $\ge 1.0\,\text{m}$.
- **Scrape Margin**: In all 29 collision cases, contact was a minor scrape with the doorpost (clearance error between $-0.001\,\text{m}$ and $-0.016\,\text{m}$, i.e., 1 to 16 mm).
- **Physical Root Cause**: Clamped chassis yaw acceleration ($\omega_{\max} = 1.2\,\text{rad/s}$) and stopping distance constraints at speeds up to $1.2\,\text{m/s}$ make it physically impossible for any controller to steer clear of an 8 cm boundary when a heavy chair enters at $+24^\circ$ heading error.

### Real Indoor Depth Benchmark (ETH Zurich FunThor Dataset)
The local depth privacy pipeline was evaluated on **20 real indoor depth frames** containing doorways from the ETH Zurich Legged Robotics FunThor benchmark:
- **Detection Success Rate**: **19 / 20 frames (95.0%)** correctly identified doorway apertures.
- **Direct Approach Accuracy**: When approaching the doorway within normal navigation corridors ($|\text{angle}| \le 70^\circ$), mean absolute width error is **0.177 m** relative to nominal ground truth.
- **Real-World Limitations**:
  1. *Glancing Approach Angles*: At oblique angles ($|\text{angle}| > 80^\circ$), perspective foreshortening and corner wall occlusion lead to aperture width underestimation (e.g. 0.05m–0.45m).
  2. *Corner Occlusion*: In 1 of 20 frames (Frame 06), doorway detection failed because the sensor was within 0.5m of an orthogonal partition, obscuring both jambs.
  3. *Unbounded Archways*: Open double-wide entryways without jamb frames are detected as wide corridors ($>1.5\,\text{m}$).

### Zero Network Calls Invariant (`test_control_loop_makes_zero_network_calls`)
Automated testing in `tests/test_simulation.py` mocks all network sockets (`socket.socket`, `socket.create_connection`, `urllib.request.urlopen`) to raise assertions if invoked. The test runs 100+ cycles of perception ray-casting, doorway detection, alpha computation, and closed-loop actuation, proving mathematically that **zero network packets** are transmitted during real-time wheelchair control.

### Reproducing the Simulation
Run the automated Monte Carlo CLI script:
```bash
python scripts/monte_carlo.py --n 1000 --seed 42 --out data/monte_carlo
```
Outputs:
- `data/monte_carlo/runs.csv` (1000 detailed per-trial telemetry rows)
- `data/monte_carlo/summary.json` (aggregate statistics, Wilson CIs, failure cases)
- `data/monte_carlo/sensitivity.csv` (physiological parameter sweep)

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
