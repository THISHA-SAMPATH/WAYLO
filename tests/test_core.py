import math

from backend import core


def test_stopping_distance_grows_with_speed():
    assert core.stopping_distance(0.0) == core.BRAKE_MARGIN_M
    assert core.stopping_distance(1.2) > core.stopping_distance(0.6) > core.stopping_distance(0.2)


def test_aeb_is_driven_by_measured_distance():
    assert core.aeb_required(0.85, 0.3)
    assert not core.aeb_required(0.85, 3.0)
    assert not core.aeb_required(0.85, None)


def test_alpha_bounds_and_emergency():
    assert core.compute_alpha(0, 1.0) == 0.0
    assert core.compute_alpha(100, 0.0) == 1.0
    assert 0.0 < core.compute_alpha(40, 0.30) < 1.0
    assert core.compute_alpha(0, 1.0, is_emergency=True) == 1.0
    assert core.compute_alpha(500, -3) == 1.0          # out-of-range inputs are clamped


def test_blend_endpoints():
    assert core.blend(1.0, 0.0, 0.0) == 1.0
    assert core.blend(1.0, 0.0, 1.0) == 0.0
    assert math.isclose(core.blend(1.0, 0.0, 0.25), 0.75)


def test_wheel_speeds_straight_and_turning():
    straight = core.wheel_speeds(0.8, 0.0)
    assert straight["left_mps"] == straight["right_mps"] == 0.8
    turn = core.wheel_speeds(0.8, 0.5)
    assert turn["right_mps"] > turn["left_mps"]
    assert math.isclose(turn["right_rad_s"], turn["right_mps"] / core.WHEEL_RADIUS_M)
