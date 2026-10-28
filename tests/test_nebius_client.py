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


def test_compile_voice_command_offline_fallback():
    nc.clear_nebius_audit_log()
    out = nc.compile_voice_command("Please go very slow and careful through this tight doorway")
    assert out["status"] == "SUCCESS"
    assert out["source"] == "fallback"
    assert 0.2 <= out["speed_cap_mps"] <= 1.0
    assert 0.05 <= out["clearance_margin_m"] <= 0.50
    assert out["door_mode"] in ("cautious", "narrow", "standard")


def test_compile_voice_command_clamps_out_of_range_model_values(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "mock_key")

    class MockResponse:
        def raise_for_status(self): pass
        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "speed_cap_mps": 99.0,          # wildly out of bounds
                            "clearance_margin_m": -5.0,     # negative out of bounds
                            "door_mode": "invalid_mode",
                            "intent_summary": "Unsafe test"
                        })
                    }
                }],
                "usage": {"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25}
            }

    monkeypatch.setattr(nc.requests, "post", lambda *a, **kw: MockResponse())
    out = nc.compile_voice_command("Go supersonic")
    assert out["source"] == "nebius_cloud"
    # Safety clamps must strictly bound values
    assert out["speed_cap_mps"] == 1.0
    assert out["clearance_margin_m"] == 0.05
    assert out["door_mode"] == "standard"


def test_narrate_incident_sanitized_caregiver_summary(monkeypatch):
    nc.clear_nebius_audit_log()
    # Offline fallback
    event = {
        "event_type": "near_miss",
        "timestamp_s": 3.2,
        "door_width_m": 0.81,
        "clearance_m": 0.07,
        "copilot_alpha": 0.75
    }
    out = nc.narrate_incident(event)
    assert out["status"] == "SUCCESS"
    assert out["source"] == "fallback"
    assert "near-miss" in out["narrative"] or "clearance" in out["narrative"]

    # Check audit log
    audit = nc.get_nebius_audit_log()
    assert len(audit) >= 1
    assert audit[-1]["task"] == "narrate_incident"
    assert audit[-1]["source"] == "fallback"
    assert "latency_ms" in audit[-1]
    assert "tokens" in audit[-1]

