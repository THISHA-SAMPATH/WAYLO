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
