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

