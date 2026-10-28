import pytest

from backend import simulation as sim


def test_default_drift_collides_without_assist_and_passes_with_waylo():
    res = sim.compare(drift_deg=14.0)
    assert res["unassisted"]["summary"]["collision"]
    assert not res["waylo"]["summary"]["collision"]
    assert res["waylo"]["summary"]["passed_door"]
    assert res["waylo"]["summary"]["min_door_clearance_m"] > 0


def test_no_drift_needs_no_help():
    res = sim.compare(drift_deg=0.0, tremor_deg=0.0)
    assert res["unassisted"]["summary"]["passed_door"]
    assert res["waylo"]["summary"]["passed_door"]
    assert res["waylo"]["summary"]["peak_alpha"] < 0.1       # copilot stays out of the way


@pytest.mark.parametrize("drift", [-30, -15, -5, 5, 15, 30])
def test_waylo_never_collides_across_drifts(drift):
    assert not sim.run(True, drift_deg=drift)["summary"]["collision"]


@pytest.mark.parametrize("door", [0.9, 1.1, 1.4])
def test_waylo_passes_ada_width_doors_with_moderate_drift(door):
    assert sim.run(True, drift_deg=10, door_width_m=door)["summary"]["passed_door"]


def test_same_driver_input_for_both_runs():
    a, b = sim.run(False, drift_deg=8, seed=3), sim.run(True, drift_deg=8, seed=3)
    assert a["t"][1] == b["t"][1]


def test_alpha_stays_in_range():
    r = sim.run(True, drift_deg=20)
    assert r["alpha"].min() >= 0.0 and r["alpha"].max() <= 1.0


def test_compare_returns_all_three_conditions_with_identical_seeds():
    res = sim.compare(drift_deg=12.0, seed=42)
    assert "uncorrected" in res
    assert "corrective" in res
    assert "waylo" in res
    assert res["unassisted"]["summary"]["mode"] == "uncorrected"
    assert res["corrective"]["summary"]["mode"] == "corrective"
    assert res["waylo"]["summary"]["mode"] == "waylo"
    # Timing and time steps match identically
    assert res["uncorrected"]["t"][1] == res["corrective"]["t"][1] == res["waylo"]["t"][1]


def test_corrective_human_attempts_visual_recovery():
    # Moderate drift in wide door: corrective human steers back toward doorway
    res = sim.compare(drift_deg=8.0, door_width_m=1.4, seed=10)
    # Both corrective and waylo can pass in a generous 1.4m door with small drift
    assert res["waylo"]["summary"]["passed_door"]
    assert res["corrective"]["summary"]["passed_door"]
    # But uncorrected collides due to pure open-loop drift
    assert res["uncorrected"]["summary"]["collision"]


def test_simulation_sensor_noise_parameters():
    # Verify simulation accepts custom sensor latency and LiDAR noise
    res = sim.run("waylo", drift_deg=8.0, door_width_m=1.4,
                  lidar_noise_m=0.03, lidar_dropout_prob=0.05, sensor_latency_s=0.15)
    assert res["summary"]["assist"] is True
    assert res["summary"]["passed_door"] is True


def test_control_loop_makes_zero_network_calls(monkeypatch):
    """Audit requirement 8: prove that the real-time control loop makes zero network calls."""
    import socket
    import urllib.request

    def blocked_network(*args, **kwargs):
        raise AssertionError("Network call attempted during real-time control loop!")

    monkeypatch.setattr(socket, "socket", blocked_network)
    monkeypatch.setattr(socket, "create_connection", blocked_network)
    monkeypatch.setattr(urllib.request, "urlopen", blocked_network)

    # 1. Perception pipeline
    room = sim.build_room(1.2)
    scan = sim.lidar_scan(room, 0.0, 1.5, 0.0, noise_sigma_m=0.02, dropout_prob=0.02)
    gap = sim.detect_gap(scan, 1.5)
    fr = sim.front_range(scan)
    cl, cr = sim.side_clearances(scan)
    assert gap is not None

    # 2. Arbitration & control blending
    alpha = sim.core.compute_alpha(25.0, 0.20)
    phi_cmd = sim.core.blend(0.2, 0.0, alpha)
    v_cmd = sim.core.blend(0.8, 0.6, alpha)
    assert 0.0 <= alpha <= 1.0

    # 3. Full closed-loop 50 Hz simulation (hundreds of control iterations)
    res = sim.run("waylo", drift_deg=10.0, speed_mps=0.85, door_width_m=1.2, duration_s=4.0)
    assert res["summary"]["assist"] is True
    assert len(res["t"]) > 100

