# WAYLO Demo Video: 3-Minute Script and Shot List

**Requirements to meet:** 3 minutes or shorter, public on YouTube, at least 1 minute showing the key application modules in action (WAYLO has no physical hardware, so the dashboard and simulations are the "robot"), and a clear view of how Nebius Token Factory and NVIDIA Nemotron are used.

## Before you record (5 minutes)

1. Add your key to `.env`, then run `python scripts/verify_nebius.py` and keep its output visible in a terminal window.
2. Start everything with `python run.py` and open `http://localhost:8501`.
3. Check the sidebar shows **🟢 Nebius Cloud: Connected**, and that a cockpit result says **Nebius AI Cloud (Live Token Factory)**. If it says "Deterministic Physical Sim Engine", the key or model name is wrong.
4. Close the walkthrough once so you can show it on camera by clicking **❓ How it works**.
5. Browser zoom 110%, 1920x1080, hide bookmarks and notifications. Record with OBS or the built-in screen recorder, with a clear voice-over.

## Timeline

| Time | On screen | Voice-over (adapt to your own words) |
|:---|:---|:---|
| 0:00 to 0:20 | Title slide, then a doorway image | "Over 75 million people use wheelchairs. For many, a 32-inch doorway is stressful and one small drift means a collision. Existing help either takes over completely or slams the brakes." |
| 0:20 to 0:40 | Architecture diagram from the README | "WAYLO is a shared-autonomy copilot. It blends the driver's joystick with NVIDIA Nemotron guidance running on Nebius Token Factory, so the person stays in control." |
| 0:40 to 0:55 | Click **❓ How it works**, step through quickly, show the α slider demo | "The dashboard explains itself. Here, α is how much the copilot helps: zero is all human, one is full copilot." |
| 0:55 to 1:25 | Doorway scenario at 14° drift. Point at the red arrow, the green arrow, clearances, α, banner | "With a 14 degree drift, the red arrow is where the chair would go alone. The green arrow is WAYLO's blended path. Clearances, hazard risk and authority update live." |
| 1:25 to 1:45 | Drag the steering slider to 40°, then switch to Tight Corridor and Dock at Table | "More drift gives more help. In the corridor speed is capped, and at the table WAYLO slows the approach." |
| 1:45 to 2:00 | Open the **🚪 Closed-Loop Doorway Run** tab; drag the time slider so the red chair hits the doorpost while the green one centres, with the LiDAR rays visible | "Same driver, same drift, run twice. Without help the chair hits the doorframe. WAYLO finds the opening in the LiDAR scan and steers through the centre." |
| 2:00 to 2:15 | Cockpit: Emergency Stop Test (red banner), then the Kinematics tab | "For a sudden obstacle, authority goes to 100 percent and the emergency brake fires. The blend becomes left and right wheel speeds through differential-drive kinematics." |
| 2:15 to 2:40 | **API Telemetry** tab showing `source: nebius_cloud` and the model name; then the terminal with `verify_nebius.py` output (model list, latency) | "Every decision here comes from NVIDIA Nemotron on Nebius Token Factory through an OpenAI-compatible endpoint. Replies are validated and clamped by a safety layer, and if the cloud is unavailable a deterministic engine takes over." |
| 2:40 to 2:55 | Swagger page at `localhost:8000/docs` or the MATLAB figure | "The same logic is exposed as a REST API for MATLAB and for future hardware." |
| 2:55 to 3:00 | End card with repo URL and license | "WAYLO: your world, your way. Code is open source under MIT." |

The "key application modules in action" minute is 0:40 to 2:15 and 2:40 to 2:55, comfortably above one minute.

**Optional:** Only show the MATLAB scripts if you have run them and the figures look right. Otherwise stay in the dashboard.

## Upload checklist

1. Export as MP4, 1080p, under 3:00.
2. YouTube Studio, then Create, then Upload. Set visibility to **Public** (not Unlisted).
3. Title: `WAYLO: Shared-Autonomy Wheelchair Copilot | NVIDIA Nemotron on Nebius Token Factory`
4. Description: two lines of summary, the GitHub URL, and "Built for the NVIDIA x Nebius Global AI Hackathon, Physical AI track".
5. Paste the URL into `README.md` ("Demo video" row) and `SUBMISSION.md`.
