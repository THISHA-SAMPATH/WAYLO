# ♿ WAYLO: YOUR WORLD. YOUR WAY.
> **AI-Powered Shared-Autonomy Mobility Copilot**  
> Accelerated with NVIDIA Nemotron & Cosmos on **Nebius AI Cloud**

---

## 🌟 Overview

**WAYLO** is a shared-autonomy mobility copilot designed for electric wheelchairs and adaptive vehicles. Rather than replacing the user's manual control, WAYLO continuously blends human steering inputs with real-time spatial vision inferences from frontier NVIDIA models (Nemotron-3-Ultra / Cosmos) hosted on **Nebius Token Factory**.

When tight corridors, doorways, or unexpected obstacles are detected, WAYLO dynamically calculates clearance buffers, applies gentle trajectory centering vectors, and engages autonomous emergency braking (AEB) when critical stopping thresholds are breached.

---

## 📐 Mathematical Blending Model

$$\mathbf{v}_{\text{final}} = (1 - \alpha) \mathbf{v}_{\text{user}} + \alpha \mathbf{v}_{\text{copilot}}$$

- **$\mathbf{v}_{\text{user}}$**: Manual joystick / steering input from the user.
- **$\mathbf{v}_{\text{copilot}}$**: Spatial correction vector computed by NVIDIA Nemotron / Cosmos.
- **$\alpha \in [0, 1]$**: Dynamic arbitration weight computed from spatial clearance buffers and hazard risk score.

---

## 🚀 Quick Start

### 1. Install Dependencies

Ensure Python 3.10+ is installed, then run:

```bash
pip install streamlit requests matplotlib numpy python-dotenv
```

### 2. Configure Environment (Optional for Live Nebius API)

Copy the example environment file and add your Nebius API key:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
NEBIUS_API_KEY=your_nebius_api_key_here
NEBIUS_BASE_URL=https://api.studio.nebius.com/v1
NEBIUS_MODEL=nvidia/nemotron-3-ultra
```

*(Note: If no API key is provided, WAYLO will automatically run in **Deterministic Offline Simulation Mode** so you can test all scenarios immediately).*

### 3. Launch the Simulation Dashboard

Run the Streamlit application:

```bash
streamlit run simulation/app.py
```

---

## 🕹️ Scenarios & Features

1. **Align with Doorway**: Guidance vector centering the wheelchair through a narrow 1.4m indoor opening.
2. **Navigate Tight Corridor**: Real-time lateral clearance monitoring between 1.2m bounded walls.
3. **Dock at Table**: Speed regulation and precision alignment for desk and workstation docking.
4. **Emergency Stop Test**: Autonomous emergency braking (AEB) triggered upon detecting unexpected obstacles.

---

## 📁 Repository Structure

```
WAYLO/
├── backend/
│   └── nebius_client.py    # Nebius Token Factory API client & offline simulation engine
├── simulation/
│   └── app.py              # Interactive Streamlit 2D room spatial visualizer & dashboard
├── .env.example            # Sample configuration for Nebius AI credentials
├── .gitignore              # Ignored files (virtual environments, secrets)
├── LICENSE                 # Project license
└── README.md               # Documentation
```
