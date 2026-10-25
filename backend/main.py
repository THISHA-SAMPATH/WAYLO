"""
WAYLO: Shared-Autonomy Mobility Copilot REST API
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

from .nebius_client import (
    analyze_spatial_frame,
    simulate_spatial_inference,
    get_api_key,
    compute_shared_autonomy_arbitration,
    DEFAULT_MODEL,
    DEFAULT_NEBIUS_BASE_URL
)
from .tavily_search import fetch_accessibility_context, get_standard_specs
from . import core, perception, simulation

# Load environment configuration
load_dotenv()

# Initialize FastAPI Application
app = FastAPI(
    title="WAYLO: Shared-Autonomy Mobility Copilot API",
    description=(
        "Physical AI middleware for power wheelchairs competing in the NVIDIA x Nebius Global AI Hackathon. "
        "Provides real-time spatial vision inferences, differential-drive kinematic arbitration, "
        "and ADA accessibility standards lookup."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend visualizers (Streamlit, MATLAB, React, WebGL)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("WAYLO_CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(","),
    allow_credentials=False,
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
    x: float
    y: float
    theta_rad: float
    linear_velocity: float
    user_steering_deg: float
    left_clearance: float
    right_clearance: float
    scenario: str = "Doorway"

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
    has_tavily = bool(tavily_key and tavily_key != "your_tavily_api_key_here")

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
        access_context = fetch_accessibility_context(query)

    frame_text = payload.frame_metadata
    if payload.lidar_pose:
        lp = payload.lidar_pose
        room = perception.build_room(float(lp.get("door_width_m", 1.4)))
        scan = perception.lidar_scan(room, float(lp.get("x", 0.0)), float(lp.get("y", 0.5)),
                                     math.radians(float(lp.get("heading_deg", 0.0))))
        frame_text = f"{frame_text}. {perception.scan_summary_text(scan, perception.detect_gap(scan, float(lp.get('y', 0.5))))}"

    # Perform perception inference
    raw_result = analyze_spatial_frame(
        image_payload=frame_text,
        user_intent=payload.user_intent,
        steering_deg=payload.steering_angle_deg,
        speed_mps=payload.velocity_mps,
        accessibility_context=access_context
    )

    # If explicit physical sensor distances were provided in the request, override or blend them
    if payload.left_sensor_dist is not None:
        raw_result["clearance_left"] = round(payload.left_sensor_dist, 2)
    if payload.right_sensor_dist is not None:
        raw_result["clearance_right"] = round(payload.right_sensor_dist, 2)
    if payload.left_sensor_dist is not None or payload.right_sensor_dist is not None:
        # Measured distances must drive arbitration too, not only the displayed numbers.
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

    # Blended forward linear velocity
    blended_v = (1.0 - alpha) * req.user_linear_vel + alpha * copilot_vel

    # Blended steering angle (degrees)
    blended_steering_deg = req.user_steering_deg + (alpha * req.copilot_correction_deg)

    # Emergency stop condition
    is_emergency = (blended_v <= 0.001) or (copilot_vel <= 0.001 and alpha > 0.8) or \
        core.aeb_required(blended_v, req.obstacle_distance_m, a_max=req.max_accel_mps2)
    if is_emergency:
        blended_v = 0.0

    # Convert steering angle to yaw rate omega (rad/s)
    # Using kinematic bicycle/unicycle approximation: omega = (v / L) * tan(delta)
    rad_steer = math.radians(blended_steering_deg)
    # Limit max angular rate to +/- 1.5 rad/s for passenger stability
    omega = max(-1.5, min(1.5, (blended_v / max(0.1, req.wheelbase_m)) * math.tan(rad_steer)))
    if is_emergency:
        omega = 0.0

    # Differential drive wheel speeds
    # v_R = v + (omega * L) / 2
    # v_L = v - (omega * L) / 2
    v_r = blended_v + (omega * req.wheelbase_m / 2.0)
    v_l = blended_v - (omega * req.wheelbase_m / 2.0)

    # Angular wheel speeds (rad/s)
    w_r = v_r / req.wheel_radius_m
    w_l = v_l / req.wheel_radius_m

    # Braking distance d = v^2 / (2 * a_max)
    stopping_dist = core.stopping_distance(blended_v, a_max=req.max_accel_mps2)

    return KinematicsBlendResponse(
        blended_linear_vel_mps=round(blended_v, 3),
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
    specs = get_standard_specs()
    return AccessibilitySearchResponse(
        query=req.query,
        standards_context=context,
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
    return {"params": req.model_dump(),
            "unassisted": _downsample(res["unassisted"]),
            "waylo": _downsample(res["waylo"])}


@app.post("/api/perception/scan", summary="Simulated 2D LiDAR scan and doorway detection", tags=["Perception"])
def perception_scan(req: ScanRequest):
    room = perception.build_room(req.door_width_m)
    scan = perception.lidar_scan(room, req.x, req.y, math.radians(req.heading_deg))
    gap = perception.detect_gap(scan, req.y)
    left, right = perception.side_clearances(scan)
    return {"ranges_m": [round(float(r), 3) for r in scan["ranges"]],
            "front_range_m": round(perception.front_range(scan), 3),
            "side_clearance_left_m": round(left, 3), "side_clearance_right_m": round(right, 3),
            "doorway": gap, "summary_text": perception.scan_summary_text(scan, gap)}

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
    # Run spatial perception
    inference = analyze_spatial_frame(
        image_payload=f"pose_x={packet.x:.2f}_y={packet.y:.2f}_theta={packet.theta_rad:.2f}",
        user_intent=f"Align with {packet.scenario}",
        steering_deg=packet.user_steering_deg,
        speed_mps=packet.linear_velocity
    )

    alpha = inference.get("arbitration_alpha", 0.5)
    correction = inference.get("steering_correction_deg", 0.0)
    is_stop = inference.get("emergency_stop", False)

    # Compute differential drive kinematics
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
        "input_pose": {"x": packet.x, "y": packet.y, "theta": packet.theta_rad},
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
    host = os.getenv("WAYLO_HOST", "127.0.0.1")
    port = int(os.getenv("WAYLO_PORT", "8000"))
    print(f"🚀 Starting WAYLO FastAPI Server on http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
