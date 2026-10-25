import json

from backend import nebius_client as nc


def test_extract_json_handles_think_blocks_fences_and_prose():
    assert nc._extract_json('<think>hmm</think>{"a": 1}') == {"a": 1}
    assert nc._extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert nc._extract_json('Sure! {"a": 3} hope that helps') == {"a": 3}


def test_sanitize_clamps_and_fills_missing_fields():
    fallback = nc.simulate_spatial_inference("Align with Doorway", 14, 0.85)
    out = nc.sanitize_inference({"arbitration_alpha": 7.5, "hazard_risk_score": 140, "clearance_left": -2}, fallback)
    assert out["arbitration_alpha"] == 1.0
    assert out["hazard_risk_score"] == 100
    assert out["clearance_left"] == 0.0
    assert "clearance_right" in out and "time_to_collision_sec" in out


def test_emergency_forces_full_authority():
    fallback = nc.simulate_spatial_inference("Align with Doorway", 14, 0.85)
    out = nc.sanitize_inference({"emergency_stop": True, "arbitration_alpha": 0.1}, fallback)
    assert out["arbitration_alpha"] == 1.0


def test_cloud_failure_falls_back_to_offline_engine(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test")
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(nc.requests, "post", boom)
    res = nc.analyze_spatial_frame(user_intent="Align with Doorway", steering_deg=14, speed_mps=0.85)
    assert "simulat" in res["source"]
    assert 0.0 <= res["arbitration_alpha"] <= 1.0
