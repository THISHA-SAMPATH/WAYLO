import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "HEALTHY"


def test_spatial_analyze_offline_defaults():
    r = client.post("/api/spatial/analyze", json={"user_intent": "Align with Doorway", "steering_angle_deg": 14}).json()
    assert 0 <= r["arbitration_alpha"] <= 1
    assert r["clearance_left"] > 0


def test_measured_sensor_distances_drive_alpha():
    base = client.post("/api/spatial/analyze", json={"user_intent": "Align with Doorway", "steering_angle_deg": 2}).json()
    tight = client.post("/api/spatial/analyze", json={"user_intent": "Align with Doorway", "steering_angle_deg": 2,
                                                       "left_sensor_dist": 0.05, "right_sensor_dist": 0.6}).json()
    assert tight["arbitration_alpha"] > base["arbitration_alpha"]


def test_blend_matches_equations():
    r = client.post("/api/kinematics/blend", json={"user_linear_vel": 0.8, "copilot_linear_vel": 0.4,
                                                    "arbitration_alpha": 0.5}).json()
    assert r["blended_linear_vel_mps"] == pytest.approx(0.6)


def test_blend_aeb_from_measured_obstacle():
    r = client.post("/api/kinematics/blend", json={"user_linear_vel": 0.9, "obstacle_distance_m": 0.3}).json()
    assert r["is_emergency_stop"] and r["blended_linear_vel_mps"] == 0.0


def test_closed_loop_endpoint():
    r = client.post("/api/simulate/closed-loop", json={"drift_deg": 14}).json()
    assert r["unassisted"]["summary"]["collision"] and r["waylo"]["summary"]["passed_door"]


def test_perception_scan_endpoint():
    r = client.post("/api/perception/scan", json={"x": 0.0, "y": 1.5}).json()
    assert len(r["ranges_m"]) == 61 and r["doorway"] is not None


def test_invalid_request_is_rejected():
    assert client.post("/api/simulate/closed-loop", json={"door_width_m": 0.2}).status_code == 422


def test_cors_rejects_unknown_origin():
    r = client.options("/health", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") is None


def test_lidar_scan_summary_reaches_the_model_prompt(monkeypatch):
    import backend.main as m
    seen = {}

    def fake(**kw):
        seen.update(kw)
        return m.simulate_spatial_inference(kw["user_intent"], kw["steering_deg"], kw["speed_mps"])
    monkeypatch.setattr(m, "analyze_spatial_frame", fake)
    r = client.post("/api/spatial/analyze", json={"lidar_pose": {"x": 0.3, "y": 2.0, "heading_deg": 5}})
    assert r.status_code == 200
    assert "2D LiDAR" in seen["image_payload"] and "Opening detected" in seen["image_payload"]


def test_copilot_step_endpoint():
    payload = {
        "user_intent": "align_doorway",
        "manual_steering_deg": 10.0,
        "speed_input": 0.8,
        "current_pose_x": 0.1,
        "current_pose_y": 1.2
    }
    r = client.post("/api/v1/copilot-step", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "SUCCESS"
    assert "final_angle" in data
    assert "arbitration_alpha" in data
    assert 0.0 <= data["alpha"] <= 1.0


def test_matlab_telemetry_endpoint():
    payload = {
        "x": 0.2,
        "y": 1.5,
        "theta_rad": 0.05,
        "linear_velocity": 0.7,
        "user_steering_deg": 5.0,
        "scenario": "Doorway"
    }
    r = client.post("/api/matlab/telemetry", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ACK"
    assert "blended_linear_vel" in data
    assert "left_wheel_speed" in data
def test_voice_command_endpoint():
    r = client.post("/api/v1/voice-command", json={"command": "Slow down for tight door"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "SUCCESS"
    assert 0.2 <= data["speed_cap_mps"] <= 1.0
    assert 0.05 <= data["clearance_margin_m"] <= 0.50


def test_narrate_incident_endpoint():
    event = {
        "event_type": "near_miss",
        "timestamp_s": 1.8,
        "door_width_m": 0.81,
        "clearance_m": 0.05,
        "copilot_alpha": 0.80
    }
    r = client.post("/api/v1/narrate-incident", json={"event": event})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "SUCCESS"
    assert "narrative" in data
    assert len(data["narrative"]) > 10


def test_nebius_audit_endpoint():
    r = client.get("/api/nebius/audit")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "SUCCESS"
    assert "calls" in data
    assert isinstance(data["calls"], list)
