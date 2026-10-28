import json
import pytest
from pathlib import Path
from scripts.monte_carlo import run_monte_carlo, wilson_score_interval, continuous_ci


def test_wilson_score_interval_bounds():
    p, low, high = wilson_score_interval(0, 10)
    assert p == 0.0
    assert low == 0.0
    assert high > 0.0

    p, low, high = wilson_score_interval(10, 10)
    assert p == 1.0
    assert low < 1.0
    assert high == 1.0

    p, low, high = wilson_score_interval(5, 10)
    assert p == 0.5
    assert 0.0 < low < 0.5 < high < 1.0


def test_continuous_ci():
    vals = [0.1, 0.2, 0.3, 0.4, 0.5]
    stats = continuous_ci(vals)
    assert stats["mean"] == pytest.approx(0.3)
    assert stats["ci_lower"] < 0.3 < stats["ci_upper"]


def test_run_monte_carlo_generates_outputs(tmp_path):
    out_dir = str(tmp_path / "mc_test")
    res = run_monte_carlo(n=6, seed=123, out_dir=out_dir)

    csv_path = Path(out_dir) / "runs.csv"
    json_path = Path(out_dir) / "summary.json"
    assert csv_path.exists()
    assert json_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "overall" in data
    assert "by_door_width" in data
    assert "waylo_failure_cases" in data
    assert "uncorrected" in data["overall"]
    assert "corrective" in data["overall"]
    assert "waylo" in data["overall"]
