import pytest
from fastapi.testclient import TestClient
from backend.ledger import MobilityLedger, DEFAULT_COST_ASSUMPTIONS, VALID_EVENT_TYPES
from backend.main import app
from backend import simulation as sim

client = TestClient(app)


def test_valid_event_types():
    assert "assist_engaged" in VALID_EVENT_TYPES
    assert "near_miss" in VALID_EVENT_TYPES
    assert "scrape" in VALID_EVENT_TYPES
    assert "collision" in VALID_EVENT_TYPES
    assert "human_rescue" in VALID_EVENT_TYPES


def test_ledger_logs_all_five_event_types():
    ledger = MobilityLedger()
    for evt in VALID_EVENT_TYPES:
        rec = ledger.log_event(evt, timestamp_s=1.5, details={"test_key": "val"})
        assert rec["event_type"] == evt
        assert rec["timestamp_s"] == 1.5

    assert len(ledger.events) == 5
    metrics = ledger.compute_metrics()
    for evt in VALID_EVENT_TYPES:
        assert metrics["event_counts"][evt] == 1


def test_invalid_event_type_raises_value_error():
    ledger = MobilityLedger()
    with pytest.raises(ValueError, match="Invalid event_type"):
        ledger.log_event("invalid_random_event")


def test_record_sim_run_and_metrics():
    ledger = MobilityLedger()
    # Run a simulation
    run_res = sim.run("waylo", drift_deg=14.0, door_width_m=0.91)
    metrics = ledger.record_sim_run(run_res, door_width_m=0.91, unassisted_collision=True)

    assert metrics["status"] == "SUCCESS"
    assert metrics["total_operating_time_s"] > 0
    assert 0.0 <= metrics["independence_ratio"] <= 1.0
    assert 0.0 <= metrics["independence_ratio_authority"] <= 1.0
    assert metrics["corrections_saved"] >= 1
    assert metrics["estimated_repair_cost_avoided_usd"] > 0
    assert "LABELED AS MODEL ASSUMPTIONS" in metrics["cost_assumptions"]["disclaimer"]


def test_configurable_cost_assumptions():
    custom_assumptions = {
        "disclaimer": "LABELED AS MODEL ASSUMPTIONS: Custom clinical trial figures.",
        "scrape_repair_cost_usd": 200.0,
        "collision_repair_cost_usd": 1200.0,
        "near_miss_averted_cost_usd": 500.0
    }
    ledger = MobilityLedger(cost_assumptions=custom_assumptions)
    ledger.corrections_saved = 2
    metrics = ledger.compute_metrics()

    assert metrics["cost_assumptions"]["collision_repair_cost_usd"] == 1200.0
    assert metrics["estimated_repair_cost_avoided_usd"] >= 2400.0


def test_ledger_api_endpoints():
    # 1. Reset
    r = client.post("/api/v1/ledger/reset")
    assert r.status_code == 200

    # 2. Log events
    r = client.post("/api/v1/ledger/event", json={
        "event_type": "near_miss",
        "timestamp_s": 2.1,
        "details": {"clearance_m": 0.06}
    })
    assert r.status_code == 200
    assert r.json()["event"]["event_type"] == "near_miss"

    # 3. Get events
    r = client.get("/api/v1/ledger/events")
    assert r.status_code == 200
    data = r.json()
    assert data["total_events"] == 1

    # 4. Get metrics
    r = client.get("/api/v1/ledger/metrics?collision_cost_usd=900.0")
    assert r.status_code == 200
    m = r.json()
    assert m["status"] == "SUCCESS"
    assert "independence_ratio" in m
    assert m["cost_assumptions"]["collision_repair_cost_usd"] == 900.0
    assert "LABELED AS MODEL ASSUMPTIONS" in m["cost_assumptions"]["disclaimer"]
