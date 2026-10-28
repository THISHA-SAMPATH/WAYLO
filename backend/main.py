"""
WAYLO Shared-Autonomy Middleware API
FastAPI Middleware connecting Electric Wheelchair Kinematics, MATLAB 3D World,
NVIDIA Nemotron / Cosmos on Nebius AI Cloud, and Tavily Accessibility Search.
"""

import os
import math
import time
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from .nebius_client import (
        analyze_spatial_frame,
        simulate_spatial_inference,
        get_api_key,
        compute_shared_autonomy_arbitration,
        DEFAULT_MODEL,
        DEFAULT_NEBIUS_BASE_URL
    )
    from .tavily_search import fetch_accessibility_context, get_standard_specs
    from .privacy_scrubber import anonymize_spatial_feed
    from . import core, perception, simulation
except (ImportError, ValueError):
    from backend.nebius_client import (
        analyze_spatial_frame,
        simulate_spatial_inference,
        get_api_key,
        compute_shared_autonomy_arbitration,
        DEFAULT_MODEL,
        DEFAULT_NEBIUS_BASE_URL
    )
    from backend.tavily_search import fetch_accessibility_context, get_standard_specs
    from backend.privacy_scrubber import anonymize_spatial_feed
    from backend import core, perception, simulation


# Load environment configuration
load_dotenv()

# Initialize FastAPI Application
app = FastAPI(
    title="WAYLO Shared-Autonomy Middleware API",
    description=(
        "Physical AI middleware for power wheelchairs competing in the NVIDIA x Nebius Global AI Hackathon. "
        "Provides real-time spatial vision inferences, differential-drive kinematic arbitration, "
        "and ADA accessibility standards lookup."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for local origins (Streamlit, MATLAB, local frontends)
local_origins = [
    "http://localhost",
    "http://localhost:8501",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1",
    "http://127.0.0.1:8501",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
]
env_origins = [o.strip() for o in os.getenv("WAYLO_CORS_ORIGINS", "").split(",") if o.strip()]
cors_origins = list(dict.fromkeys(local_origins + env_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class SpatialInferenceRequest(BaseModel):
    frame_metadata: str = Field(
        default="frame_rgbd_001",
        description="Sensor frame identifier or base64 visual token"
    )
    user_intent: str = Field(
        default="Align with Doorway",
        description="Target intent: 'Align with Doorway', 'Navigate Tight Corridor', 'Dock at Table', 'Emergency Stop Test'"
    )
    lidar_pose: Optional[dict] = Field(
        default=None,
        description="Optional simulated LiDAR pose {x, y, heading_deg, door_width_m}. When given, the ray-cast scan "
                    "summary (ranges, detected opening) is added to the model prompt as real sensor context."
    )
    steering_angle_deg: float = Field(
        default=0.0,
        ge=-45.0,
        le=45.0,
        description="Manual steering angle command in degrees [-45, +45]"
    )
    velocity_mps: float = Field(
        default=0.8,
        ge=0.0,
        le=2.0,
        description="Desired forward velocity in m/s [0.0 to 2.0]"
    )
    left_sensor_dist: Optional[float] = Field(
        default=None,
        description="Optional ultrasonic/LiDAR rangefinder reading on the left side (meters)"
    )
    right_sensor_dist: Optional[float] = Field(
        default=None,
        description="Optional ultrasonic/LiDAR rangefinder reading on the right side (meters)"
    )
    forward_sensor_dist: Optional[float] = Field(
        default=None,
        description="Optional forward LiDAR rangefinder reading (meters)"
    )
    query_accessibility: bool = Field(
        default=False,
        description="Whether to query Tavily for real-time accessibility standards"
    )
    accessibility_query: Optional[str] = Field(
        default=None,
        description="Custom query for Tavily accessibility search"
    )

class SpatialInferenceResponse(BaseModel):
    status: str
    source: str
    model: str
    user_intent: str
    steering_correction_deg: float
    arbitration_alpha: float
    speed_buffer_override: str
    recommended_velocity: str
    clearance_left: float
    clearance_right: float
    hazard_risk_score: int
    emergency_stop: bool
    time_to_collision_sec: float
    spatial_summary: str
    accessibility_context: Optional[str] = None
    api_notice: Optional[str] = None

class KinematicsBlendRequest(BaseModel):
    user_linear_vel: float = Field(
        default=0.8,
        description="User commanded linear velocity (m/s)"
    )
    user_steering_deg: float = Field(
        default=0.0,
        description="User commanded steering angle in degrees"
    )
    copilot_correction_deg: float = Field(
        default=0.0,
        description="Copilot angular adjustment recommendation in degrees"
    )
    copilot_linear_vel: Optional[float] = Field(
        default=None,
        description="Copilot recommended safe velocity (m/s)"
    )
    arbitration_alpha: Optional[float] = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Shared-autonomy blending weight alpha in [0, 1]"
    )
    wheelbase_m: float = Field(
        default=0.60,
        description="Wheelchair track width / wheelbase L in meters"
    )
    wheel_radius_m: float = Field(
        default=0.16,
        description="Wheel radius r in meters"
    )
    max_accel_mps2: float = Field(
        default=2.0,
        description="Maximum braking deceleration in m/s^2"
    )
    obstacle_distance_m: Optional[float] = Field(
        default=None,
        description="Measured distance to the nearest obstacle ahead (m). Triggers AEB when within stopping distance."
    )

class KinematicsBlendResponse(BaseModel):
    blended_linear_vel_mps: float
    blended_angular_vel_rad_s: float
    blended_steering_deg: float
    left_wheel_rad_s: float
    right_wheel_rad_s: float
    left_wheel_mps: float
    right_wheel_mps: float
    stopping_distance_m: float
    arbitration_alpha: float
    is_emergency_stop: bool

class AccessibilitySearchRequest(BaseModel):
    query: str = Field(
        default="ADA wheelchair doorway minimum clear width",
        description="Query to search accessibility building codes and standards"
    )

class AccessibilitySearchResponse(BaseModel):
    query: str
    standards_context: str
    standard_specs: Dict[str, Any]

class MatlabTelemetryPacket(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    x: float = Field(default=0.0, description="X coordinate (m)")
    y: float = Field(default=0.0, description="Y coordinate (m)")
    z: Optional[float] = Field(default=0.0, description="Optional Z coordinate (m)")
    theta_rad: float = Field(default=0.0, description="Heading angle in radians")
    linear_velocity: float = Field(default=0.8, description="Linear velocity (m/s)")
    user_steering_deg: float = Field(default=0.0, description="User steering angle (deg)")
    left_clearance: Optional[float] = Field(default=0.4, description="Left clearance (m)")
    right_clearance: Optional[float] = Field(default=0.4, description="Right clearance (m)")
    scenario: Optional[str] = Field(default="Doorway", description="Scenario identifier")

class CopilotStepRequest(BaseModel):
    user_intent: str = Field(
        default="align_doorway",
        description="User navigational intent (e.g. align_doorway, navigate_corridor)"
    )
    manual_steering_deg: float = Field(
        default=0.0,
        description="Manual steering angle command in degrees"
    )
    speed_input: float = Field(
        default=0.8,
        description="Desired forward velocity in m/s"
    )
    current_pose_x: float = Field(
        default=0.0,
        description="Current wheelchair X coordinate in meters"
    )
    current_pose_y: float = Field(
        default=0.0,
        description="Current wheelchair Y coordinate in meters"
    )

# ==============================================================================
# API Endpoints
# ==============================================================================

@app.get("/", summary="WAYLO System Overview", tags=["System"])
def root_overview():
    """Returns system status, active Nebius model, and API route index."""
    has_nebius = bool(get_api_key())
    return {
        "project": "WAYLO",
        "tagline": "YOUR WORLD. YOUR WAY.",
        "description": "Shared-Autonomy Spatial Copilot for Power Wheelchairs",
        "track": "NVIDIA x Nebius Global AI Hackathon (Physical AI)",
        "nebius_cloud_status": "ACTIVE_AUTHENTICATED" if has_nebius else "OFFLINE_SIMULATION_FALLBACK",
        "default_model": DEFAULT_MODEL,
        "endpoints": {
            "health": "/health",
            "copilot_step": "/api/v1/copilot-step",
            "spatial_analyze": "/api/spatial/analyze",
            "kinematics_blend": "/api/kinematics/blend",
            "accessibility_search": "/api/accessibility/search",
            "scenarios": "/api/scenarios",
            "matlab_telemetry": "/api/matlab/telemetry",
            "documentation": "/docs"
        }
    }

@app.get("/health", summary="Healthcheck & Services Status", tags=["System"])
def healthcheck():
    """Verifies backend operational status and Nebius / Tavily integrations."""
    nebius_key = get_api_key()
    tavily_key = os.getenv("TAVILY_API_KEY")
    has_tavily = bool(tavily_key and tavily_key not in ("your_tavily_api_key_here", "tvly-your_tavily_key_here"))

    return {
        "status": "HEALTHY",
        "timestamp": time.time(),
        "services": {
            "nebius_ai_studio": {
                "configured": bool(nebius_key),
                "base_url": DEFAULT_NEBIUS_BASE_URL,
                "model": DEFAULT_MODEL
            },
            "tavily_search": {
                "configured": has_tavily
            },
            "kinematics_engine": {
                "status": "ONLINE",
                "model": "Differential Drive Unicycle (Wheelbase L=0.6m, r=0.16m)"
            }
        }
    }

@app.post(
    "/api/v1/copilot-step",
    summary="Shared-Autonomy Single Step Arbitration",
    tags=["Copilot"]
)
def copilot_step(req: CopilotStepRequest):
    """
    Step-by-step shared-autonomy arbitration endpoint:
    - Accepts user_intent, manual_steering_deg, speed_input, current_pose_x, and current_pose_y.
    - Executes spatial inference via analyze_spatial_frame.
    - Computes arbitration weight alpha scaling with perceived clearance deficit.
    - Blends human vs. AI inputs: final_angle = (1 - alpha) * user_angle + alpha * copilot_angle.
    """
    user_angle = req.manual_steering_deg
    user_speed = req.speed_input

    frame_payload = f"pose_x={req.current_pose_x:.2f}_y={req.current_pose_y:.2f}"
    inference = analyze_spatial_frame(
        image_payload=frame_payload,
        user_intent=req.user_intent,
        steering_deg=user_angle,
        speed_mps=user_speed
    )

    left_c = float(inference.get("clearance_left_m", inference.get("clearance_left", 0.42)))
    right_c = float(inference.get("clearance_right_m", inference.get("clearance_right", 0.38)))
    min_clearance = min(left_c, right_c)

    min_safe_clearance = 0.40
    clearance_deficit = max(0.0, min_safe_clearance - min_clearance)

    base_alpha = float(inference.get("arbitration_alpha", 0.0))
    deficit_alpha = min(1.0, clearance_deficit / min_safe_clearance)
    alpha = round(max(base_alpha, deficit_alpha), 3)

    is_emergency = bool(inference.get("emergency_stop", False))
    if is_emergency:
        alpha = 1.0

    copilot_correction = float(inference.get("steering_correction_deg", 0.0))
    copilot_angle = user_angle + copilot_correction

    # Shared-autonomy arbitration formula:
    # final_angle = (1 - alpha) * user_angle + alpha * copilot_angle
    final_angle = round((1.0 - alpha) * user_angle + alpha * copilot_angle, 2)
    final_speed = 0.0 if is_emergency else round(min(user_speed, (1.0 - 0.5 * alpha) * user_speed), 2)

    return {
        "status": "SUCCESS",
        "user_intent": req.user_intent,
        "current_pose": {"x": req.current_pose_x, "y": req.current_pose_y},
        "manual_steering_deg": user_angle,
        "user_angle": user_angle,
        "copilot_correction_deg": copilot_correction,
        "copilot_angle": round(copilot_angle, 2),
        "arbitration_alpha": alpha,
        "alpha": alpha,
        "clearance_deficit": round(clearance_deficit, 3),
        "final_angle": final_angle,
        "blended_steering_deg": final_angle,
        "speed_input": user_speed,
        "final_speed": final_speed,
        "clearance_left_m": left_c,
        "clearance_right_m": right_c,
        "clearance_left": left_c,
        "clearance_right": right_c,
        "emergency_stop": is_emergency,
        "hazard_risk_score": inference.get("hazard_risk_score", 10),
        "spatial_summary": inference.get("spatial_summary", ""),
        "inference_source": inference.get("source", "copilot_engine")
    }

@app.post(
    "/api/spatial/analyze",
    response_model=SpatialInferenceResponse,
    summary="Perception-to-Trajectory Copilot Inference",
    tags=["Perception"]
)
def analyze_spatial_telemetry(payload: SpatialInferenceRequest):
    """
    Submits user steering, velocity, and visual frame context to NVIDIA Nemotron / Cosmos on
    Nebius AI Cloud. Computes clearance buffers, hazard risk score, and shared-autonomy correction.
    """
    access_context = None
    if payload.query_accessibility or payload.accessibility_query:
        query = payload.accessibility_query or f"wheelchair standard for {payload.user_intent}"
        res = fetch_accessibility_context(query)
        access_context = res.get("formatted_context", str(res)) if isinstance(res, dict) else str(res)

    frame_text = payload.frame_metadata
    if payload.lidar_pose:
        lp = payload.lidar_pose
        room = perception.build_room(float(lp.get("door_width_m", 1.4)))
        scan = perception.lidar_scan(room, float(lp.get("x", 0.0)), float(lp.get("y", 0.5)),
                                     math.radians(float(lp.get("heading_deg", 0.0))))
        frame_text = f"{frame_text}. {perception.scan_summary_text(scan, perception.detect_gap(scan, float(lp.get('y', 0.5))))}"

    raw_result = analyze_spatial_frame(
        image_payload=frame_text,
        user_intent=payload.user_intent,
        steering_deg=payload.steering_angle_deg,
        speed_mps=payload.velocity_mps,
        accessibility_context=access_context
    )

    if payload.left_sensor_dist is not None:
        raw_result["clearance_left"] = round(payload.left_sensor_dist, 2)
    if payload.right_sensor_dist is not None:
        raw_result["clearance_right"] = round(payload.right_sensor_dist, 2)
    if payload.left_sensor_dist is not None or payload.right_sensor_dist is not None:
        min_clear = min(raw_result["clearance_left"], raw_result["clearance_right"])
        raw_result["arbitration_alpha"] = round(max(
            float(raw_result.get("arbitration_alpha", 0.0)),
            core.compute_alpha(float(raw_result.get("hazard_risk_score", 0)), min_clear,
                               bool(raw_result.get("emergency_stop", False)))), 3)

    return SpatialInferenceResponse(**raw_result)

@app.post(
    "/api/kinematics/blend",
    response_model=KinematicsBlendResponse,
    summary="Physical Shared-Autonomy Kinematic Blending",
    tags=["Kinematics"]
)
def blend_kinematics(req: KinematicsBlendRequest):
    """
    Executes the shared-autonomy mathematical arbitration model:
        v_final = (1 - alpha) * v_user + alpha * v_copilot
        theta_final = (1 - alpha) * theta_user + alpha * (theta_user + copilot_correction)

    Converts linear and angular velocities into differential drive wheel velocities:
        v_R = v + (omega * L) / 2
        v_L = v - (omega * L) / 2
        omega_wheel = v_wheel / r
    """
    alpha = max(0.0, min(1.0, req.arbitration_alpha if req.arbitration_alpha is not None else 0.5))
    copilot_vel = req.copilot_linear_vel if req.copilot_linear_vel is not None else req.user_linear_vel

    v = (1.0 - alpha) * req.user_linear_vel + alpha * copilot_vel
    stopping_dist = (v ** 2) / (2.0 * req.max_accel_mps2)

    is_emergency = False
    if req.obstacle_distance_m is not None:
        if req.obstacle_distance_m <= (stopping_dist + 0.15):
            is_emergency = True
            v = 0.0
            alpha = 1.0

    blended_steering_deg = req.user_steering_deg + (alpha * req.copilot_correction_deg)
    steering_rad = math.radians(blended_steering_deg)
    omega = (v / req.wheelbase_m) * math.tan(steering_rad) if not is_emergency else 0.0

    v_r = v + (omega * req.wheelbase_m / 2.0)
    v_l = v - (omega * req.wheelbase_m / 2.0)

    w_r = v_r / req.wheel_radius_m
    w_l = v_l / req.wheel_radius_m

    return KinematicsBlendResponse(
        blended_linear_vel_mps=round(v, 3),
        blended_angular_vel_rad_s=round(omega, 3),
        blended_steering_deg=round(blended_steering_deg, 2),
        left_wheel_rad_s=round(w_l, 3),
        right_wheel_rad_s=round(w_r, 3),
        left_wheel_mps=round(v_l, 3),
        right_wheel_mps=round(v_r, 3),
        stopping_distance_m=round(stopping_dist, 3),
        arbitration_alpha=alpha,
        is_emergency_stop=is_emergency
    )

@app.post(
    "/api/accessibility/search",
    response_model=AccessibilitySearchResponse,
    summary="Live Accessibility Code Search via Tavily",
    tags=["Accessibility"]
)
def search_accessibility_standards(req: AccessibilitySearchRequest):
    """Queries Tavily API or standards catalog for ADA / ISO 7176 spatial accessibility regulations."""
    context = fetch_accessibility_context(req.query)
    context_str = context.get("formatted_context", str(context)) if isinstance(context, dict) else str(context)
    specs = get_standard_specs()
    return AccessibilitySearchResponse(
        query=req.query,
        standards_context=context_str,
        standard_specs=specs
    )

# ------------------------------------------------------------------------------
# Closed-loop simulation and simulated LiDAR perception
# ------------------------------------------------------------------------------
class ClosedLoopRequest(BaseModel):
    drift_deg: float = Field(default=14.0, ge=-45, le=45, description="Driver heading drift (degrees)")
    speed_mps: float = Field(default=0.85, gt=0.1, le=1.8)
    door_width_m: float = Field(default=1.4, ge=0.80, le=2.0, description="Clear door opening (ADA minimum 0.815 m)")
    tremor_deg: float = Field(default=2.0, ge=0, le=8, description="Hand-tremor amplitude (degrees)")
    duration_s: float = Field(default=9.0, gt=1, le=20)

class ScanRequest(BaseModel):
    x: float = 0.0
    y: float = 0.5
    heading_deg: float = 0.0
    door_width_m: float = 1.4

def _downsample(sim: dict, step: int = 5) -> dict:
    out = {k: [round(float(x), 3) for x in v[::step]] for k, v in sim.items() if k != "summary"}
    out["summary"] = sim["summary"]
    return out

@app.post("/api/simulate/closed-loop", summary="Unassisted vs WAYLO closed-loop doorway run", tags=["Simulation"])
def simulate_closed_loop(req: ClosedLoopRequest):
    """Runs the same driver input twice (no assist, then WAYLO) through a simulated LiDAR doorway."""
    res = simulation.compare(**req.model_dump())
    return {
        "params": req.model_dump(),
        "unassisted": _downsample(res["unassisted"]),
        "waylo": _downsample(res["waylo"])
    }

@app.post("/api/perception/scan", summary="Simulated 2D LiDAR scan and doorway detection", tags=["Perception"])
def perception_scan(req: ScanRequest):
    room = perception.build_room(req.door_width_m)
    scan = perception.lidar_scan(room, req.x, req.y, math.radians(req.heading_deg))
    gap = perception.detect_gap(scan, req.y)
    left, right = perception.side_clearances(scan)
    return {
        "ranges_m": [round(float(r), 3) for r in scan["ranges"]],
        "front_range_m": round(perception.front_range(scan), 3),
        "side_clearance_left_m": round(left, 3),
        "side_clearance_right_m": round(right, 3),
        "doorway": gap,
        "summary_text": perception.scan_summary_text(scan, gap)
    }

@app.get("/api/scenarios", summary="Predefined Indoor Physical Scenarios", tags=["Scenarios"])
def get_indoor_scenarios():
    """Returns geometric definitions of benchmark indoor testing scenarios."""
    return {
        "scenarios": [
            {
                "id": "doorway_centering",
                "name": "Align with Doorway",
                "description": "Centering through a 1.4m doorway threshold between two walls at Y=4.5m",
                "boundary_x": [-2.8, 2.8],
                "doorway_opening": [-0.7, 0.7],
                "doorway_y": 4.5,
                "target_point": [0.0, 5.0],
                "default_steering_deg": 12.0
            },
            {
                "id": "corridor_navigation",
                "name": "Navigate Tight Corridor",
                "description": "1.2m narrow corridor bounded between X=-0.6m and X=+0.6m from Y=2.0m to Y=5.5m",
                "boundary_x": [-0.6, 0.6],
                "corridor_length_m": 3.5,
                "target_point": [0.0, 5.5],
                "default_steering_deg": -15.0
            },
            {
                "id": "table_docking",
                "name": "Dock at Table",
                "description": "Approaching a workstation desk with 1.0m docking slot, requiring controlled deceleration",
                "table_bounds": {"x_min": -1.4, "x_max": 1.4, "y_min": 3.8, "y_max": 5.2},
                "docking_point": [0.0, 3.8],
                "default_steering_deg": 8.0
            },
            {
                "id": "dynamic_obstacle",
                "name": "Emergency Stop Test",
                "description": "Unscheduled dynamic hazard appearing at Y=2.5m directly in trajectory path",
                "obstacle_pos": [0.0, 2.5],
                "safety_radius_m": 0.85,
                "default_steering_deg": 0.0
            }
        ]
    }

@app.post("/api/matlab/telemetry", summary="MATLAB / Simulink Telemetry Bridge", tags=["MATLAB"])
def matlab_telemetry_hook(packet: MatlabTelemetryPacket):
    """
    Dedicated endpoint optimized for high-frequency polling from MATLAB / Simulink.
    Receives current physical pose (x, y, theta) and computes optimal control corrections.
    """
    inference = analyze_spatial_frame(
        image_payload=f"pose_x={packet.x:.2f}_y={packet.y:.2f}_theta={packet.theta_rad:.2f}",
        user_intent=f"Align with {packet.scenario or 'Doorway'}",
        steering_deg=packet.user_steering_deg,
        speed_mps=packet.linear_velocity
    )

    alpha = inference.get("arbitration_alpha", 0.5)
    correction = inference.get("steering_correction_deg", 0.0)
    is_stop = inference.get("emergency_stop", False)

    v_rec = 0.0 if is_stop else packet.linear_velocity
    blended_v = (1.0 - alpha) * packet.linear_velocity + alpha * v_rec
    blended_steer = packet.user_steering_deg + (alpha * correction)
    rad_steer = math.radians(blended_steer)
    omega = (blended_v / 0.60) * math.tan(rad_steer) if not is_stop else 0.0

    v_r = blended_v + (omega * 0.60 / 2.0)
    v_l = blended_v - (omega * 0.60 / 2.0)

    return {
        "status": "ACK",
        "timestamp": time.time(),
        "input_pose": {"x": packet.x, "y": packet.y, "z": packet.z, "theta": packet.theta_rad},
        "copilot_correction_deg": correction,
        "arbitration_alpha": alpha,
        "blended_linear_vel": round(blended_v, 3),
        "blended_angular_vel": round(omega, 3),
        "left_wheel_speed": round(v_l / 0.16, 3),
        "right_wheel_speed": round(v_r / 0.16, 3),
        "emergency_stop": is_stop,
        "hazard_risk_score": inference.get("hazard_risk_score", 10),
        "spatial_summary": inference.get("spatial_summary", "")
    }

# ==============================================================================
# Main Runner
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
