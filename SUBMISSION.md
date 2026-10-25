# WAYLO: Hackathon Submission Package

Copy each section into the matching field of the submission form. Anything marked **[FILL IN]** needs your own information before you submit.

---

## 1. Basics

| Field | Value |
|:---|:---|
| Project name | WAYLO: Your World. Your Way. |
| One-line pitch | A shared-autonomy copilot that keeps a power wheelchair centred in doorways and corridors, blending the driver's joystick with NVIDIA Nemotron guidance instead of taking control away. |
| Category / track | **Physical AI** |
| Public code repository | **[FILL IN]** `https://github.com/<your-username>/WAYLO` |
| License | MIT (see `LICENSE`, shown at the top of the repository page) |
| Working demo URL | Not required for Physical AI submissions |
| Demo video (public YouTube, 3 min or less) | **[FILL IN]** |
| Builders & Brews city (only if you attended) | **[FILL IN, or leave blank]** |

---

## 2. Project description

### What we created
WAYLO is a physical-AI copilot for electric wheelchairs. It watches the driver's joystick command and the surrounding space (doorway, corridor, table, sudden obstacle) and gently corrects drift so the chair passes through narrow openings without scraping. It never replaces the driver: a continuous authority weight α between 0 and 1 blends human and copilot commands, and full automatic braking is kept only for imminent hazards. The project includes a FastAPI middleware, an interactive Streamlit cockpit with a guided walkthrough, and MATLAB kinematics and 3D simulations.

### Why we created it
More than 75 million people rely on a wheelchair. For people with tremor, cerebral palsy, ALS or spinal-cord injury, a standard 32-inch (0.81 m) doorway is a daily source of stress and collisions. Today's assistance is usually all-or-nothing: full automation that removes dignity and control, or an abrupt hard brake. WAYLO keeps the person in charge and only helps as much as the situation needs.

### How it works
1. The driver's intent, steering angle and speed are sent to the FastAPI backend.
2. The backend optionally fetches ADA / ISO 7176 clearance text through Tavily.
3. NVIDIA Nemotron on Nebius Token Factory returns a JSON assessment: left and right clearance, hazard score, steering correction, recommended speed and a plain-language explanation.
4. A deterministic safety layer fills missing fields and clamps every value to a safe range.
5. α is computed from hazard and clearance deficit, and the final command is `v = (1-α)·v_user + α·v_copilot`, converted to left and right wheel speeds with differential-drive kinematics.
6. If no key is configured or the cloud call fails, a deterministic physics engine answers, so the system always keeps running.

### Honest scope
The Nemotron call reasons over a text description of the scene, which in simulation includes a summary of a ray-cast LiDAR scan. The 50 Hz control loop, doorway detection and emergency braking are deterministic and do not wait for the cloud. Real LiDAR or depth hardware and a physical chair are the next milestone.

---

## 3. NVIDIA and Nebius usage

| Item | How it is used | Where in the repo |
|:---|:---|:---|
| NVIDIA Nemotron-3-Ultra (`nvidia/Nemotron-3-Ultra-550b-a55b`) | Spatial reasoning: clearances, hazard score, steering correction, explanation | `backend/nebius_client.py` |
| Other NVIDIA models (Nemotron-3-Super, Nemotron-3-Nano, Cosmos3-Super-Reasoner) | Selectable in the dashboard sidebar for comparison | `simulation_streamlit/app.py` |
| Nebius Token Factory | Hosts the models behind an OpenAI-compatible endpoint (`/models`, `/chat/completions`) | `backend/nebius_client.py`, `scripts/verify_nebius.py` |
| Where Token Factory sped up our workflow | **[FILL IN from your own experience, for example: one HTTPS call and no SDK; switching models by changing one string; measured latency from `verify_nebius.py`]** | |
| Other Nebius tools or services | **[FILL IN, or write "None"]** | |
| Tavily Search API | Live accessibility standards context | `backend/tavily_search.py` |

---

## 4. If the project existed before the Submission Period

Write a short explanation of what was significantly updated during the Submission Period. Check your git history to confirm dates:

```bash
git log --since="<submission-period-start-date>" --pretty="%h %ad %s" --date=short
```

Candidate items (keep only those whose commits fall inside the period):

| Area | Update |
|:---|:---|
| Cloud integration | Moved to the Nebius Token Factory endpoint and current NVIDIA model IDs; added `scripts/verify_nebius.py` for live checks |
| Safety | Added output validation (`sanitize_inference`) that fills missing fields and clamps α, risk and clearances; tolerant parsing of reasoning-model replies |
| User experience | Added an interactive five-step walkthrough (`simulation_streamlit/guided_app.py`), a one-command launcher (`run.py`) and a full visual theme (`theme.css`, `.streamlit/config.toml`) |
| Perception and benchmark | Added a simulated 2D LiDAR with doorway detection from the scan and a closed-loop unassisted-versus-WAYLO benchmark (39-case sweep: WAYLO passed 39, unassisted collided in 34); distance-based emergency braking |
| Quality | Shared core module, 37 automated tests, GitHub Actions CI, restricted CORS and localhost binding |
| Documentation | Added this submission package, a demo-video script and a judge-facing README section |
| **[FILL IN]** | Anything else you built during the period |

---

## 5. Feedback on Nebius and NVIDIA tools

Write this from your own experience; judges can tell. Short, specific notes are best. Run `python scripts/verify_nebius.py` first and paste its measured output where indicated.

**Nebius Token Factory**
- Getting started (account, API key, finding the right model ID and base URL): **[FILL IN]**
- Model catalogue and naming (anything confusing, renamed or retired): **[FILL IN]**
- Latency and reliability, with measured numbers (time to first response, JSON reliability): **[FILL IN, paste `latency_s` and `usage`]**
- Documentation quality and what you wished existed: **[FILL IN]**
- Pricing and credits experience: **[FILL IN]**

**Nebius AI Cloud (if you used it)**
- **[FILL IN, or write "Not used"]**

**NVIDIA Nemotron / Cosmos**
- Quality of the structured JSON output for a control-style task: **[FILL IN]**
- Behaviour of the reasoning model (extra text or think blocks, consistency at low temperature): **[FILL IN]**
- Which model size worked best for the latency you need: **[FILL IN]**
- What you would like NVIDIA to add (for example native image or depth input examples for physical AI): **[FILL IN]**

---

## 6. Submission checklist

| Requirement | Status | Where |
|:---|:---|:---|
| Working project using Nemotron on Token Factory | Ready; confirm with your key | `scripts/verify_nebius.py`, `python run.py` |
| Category | Done | Physical AI |
| Project description | Done | Section 2 |
| Working demo URL | Not required (Physical AI) | |
| Demo video, 3 min or less, public on YouTube, 1 min or more of key modules in action | **You must record** | `docs/DEMO_VIDEO_SCRIPT.md` |
| Public repo with open-source license visible | Make repo public and push | `LICENSE` (MIT), badge in README |
| README with setup and running guidance | Done | `README.md` |
| README highlights Nemotron, Token Factory and other Nebius services | Done | README "Hackathon Submission at a Glance" |
| Feedback on Nebius and NVIDIA tools | **You must complete** | Section 5 |
| Written explanation of updates (if project pre-existed) | **You must confirm** | Section 4 |
| Builders & Brews city (if attended) | Optional | Section 1 |
