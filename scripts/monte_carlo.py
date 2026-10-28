"""
Reproducible Monte Carlo Simulation for WAYLO Shared-Autonomy Wheelchair Copilot.

Evaluates 3 experimental conditions across randomized doorway scenarios:
1. 'uncorrected': Open-loop driver with constant heading drift and tremor.
2. 'corrective': Closed-loop human driver with visual feedback, reaction delay (0.2-0.6s),
   hand tremor, joystick noise, and fatigue accumulating over time.
3. 'waylo': Corrective human driver assisted by WAYLO shared-autonomy copilot (local perception + dynamic alpha arbitration).

CLI Args:
  --n: Number of randomized trials (default: 100)
  --seed: Master random seed for reproducibility (default: 42)
  --out: Output directory for runs.csv and summary.json (default: data/monte_carlo)
"""

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import simulation as sim

DOOR_WIDTHS = [0.81, 0.91, 1.0, 1.1, 1.4]


def wilson_score_interval(successes: int, total: int, z: float = 1.95996) -> Tuple[float, float, float]:
    """
    Computes sample proportion and 95% two-sided Wilson score confidence interval.
    Returns (proportion, ci_lower, ci_upper).
    """
    if total == 0:
        return 0.0, 0.0, 0.0
    p_hat = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p_hat + z2 / (2.0 * total)) / denom
    margin = (z / denom) * math.sqrt((p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * total * total)))
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return round(p_hat, 4), round(lower, 4), round(upper, 4)


def continuous_ci(values: List[float], z: float = 1.95996) -> Dict[str, float]:
    """Computes mean, std, median, and 95% confidence interval for continuous metrics."""
    if not values:
        return {"mean": 0.0, "std": 0.0, "median": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "count": 0}
    arr = np.array(values, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    median = float(np.median(arr))
    margin = (z * std / math.sqrt(len(arr))) if len(arr) > 1 else 0.0
    return {
        "mean": round(mean, 4),
        "std": round(std, 4),
        "median": round(median, 4),
        "ci_lower": round(mean - margin, 4),
        "ci_upper": round(mean + margin, 4),
        "count": len(arr)
    }


def run_monte_carlo(n: int = 100, seed: int = 42, out_dir: str = "data/monte_carlo") -> Dict[str, Any]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)

    trials_data: List[Dict[str, Any]] = []
    waylo_failures: List[Dict[str, Any]] = []

    print(f"=================================================================")
    print(f"  WAYLO REPRODUCIBLE MONTE CARLO (N={n}, Seed={seed})")
    print(f"=================================================================")

    # Run simulations
    for trial_idx in range(n):
        trial_seed = int(rng.integers(0, 1_000_000))
        trial_rng = np.random.default_rng(trial_seed)

        door_width = float(trial_rng.choice(DOOR_WIDTHS))
        drift = float(trial_rng.uniform(-25.0, 25.0))
        tremor = float(trial_rng.uniform(0.5, 3.5))
        delay = float(trial_rng.uniform(0.2, 0.6))
        fatigue = float(trial_rng.uniform(0.02, 0.08))
        speed = float(trial_rng.uniform(0.6, 1.0))
        noise = float(trial_rng.uniform(0.5, 1.5))

        sim_params = {
            "drift_deg": drift,
            "speed_mps": speed,
            "door_width_m": door_width,
            "tremor_deg": tremor,
            "seed": trial_seed,
            "reaction_delay_s": delay,
            "fatigue_rate": fatigue,
            "joystick_noise_deg": noise,
            "visual_gain": 1.2
        }

        # Run all three conditions with identical randomized parameters and seed
        res = sim.compare(**sim_params)

        for condition in ["uncorrected", "corrective", "waylo"]:
            run_data = res[condition]
            summary = run_data["summary"]

            passed = bool(summary["passed_door"])
            collision = bool(summary["collision"])
            min_clearance = summary["min_door_clearance_m"]
            peak_alpha = summary.get("peak_alpha", 0.0)
            duration_s = summary.get("duration_s", 0.0)
            collision_time = summary.get("collision_time_s")

            row = {
                "trial_id": trial_idx,
                "trial_seed": trial_seed,
                "condition": condition,
                "door_width_m": door_width,
                "drift_deg": round(drift, 2),
                "tremor_deg": round(tremor, 2),
                "reaction_delay_s": round(delay, 3),
                "fatigue_rate": round(fatigue, 3),
                "speed_mps": round(speed, 2),
                "joystick_noise_deg": round(noise, 2),
                "collision": collision,
                "passed_door": passed,
                "min_clearance_m": min_clearance if min_clearance is not None else -0.1,
                "peak_alpha": peak_alpha,
                "duration_s": duration_s,
                "collision_time_s": collision_time if collision_time is not None else ""
            }
            trials_data.append(row)

            if condition == "waylo" and (collision or not passed):
                waylo_failures.append({
                    "trial_id": trial_idx,
                    "door_width_m": door_width,
                    "drift_deg": round(drift, 2),
                    "tremor_deg": round(tremor, 2),
                    "reaction_delay_s": round(delay, 3),
                    "fatigue_rate": round(fatigue, 3),
                    "speed_mps": round(speed, 2),
                    "collision": collision,
                    "collision_time_s": collision_time,
                    "min_clearance_m": min_clearance,
                    "aeb_triggered": summary.get("aeb_triggered", False),
                    "reason": "Wall Collision" if collision else "Did Not Clear Doorway in Time"
                })

    # Save CSV
    csv_file = out_path / "runs.csv"
    fieldnames = list(trials_data[0].keys())
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trials_data)

    # Compute breakdown by door width and overall
    conditions = ["uncorrected", "corrective", "waylo"]
    by_door_width: Dict[str, Dict[str, Any]] = {}

    for w in DOOR_WIDTHS:
        w_str = f"{w:.2f}"
        by_door_width[w_str] = {}
        for c in conditions:
            subset = [r for r in trials_data if abs(r["door_width_m"] - w) < 1e-4 and r["condition"] == c]
            tot = len(subset)
            colls = sum(1 for r in subset if r["collision"])
            passes = sum(1 for r in subset if r["passed_door"])
            clearances = [r["min_clearance_m"] for r in subset if r["min_clearance_m"] is not None]

            c_rate, c_low, c_high = wilson_score_interval(colls, tot)
            p_rate, p_low, p_high = wilson_score_interval(passes, tot)
            clear_stats = continuous_ci(clearances)

            by_door_width[w_str][c] = {
                "total_runs": tot,
                "collision_count": colls,
                "collision_rate": c_rate,
                "collision_ci_95": [c_low, c_high],
                "pass_count": passes,
                "pass_rate": p_rate,
                "pass_ci_95": [p_low, p_high],
                "min_door_clearance": clear_stats
            }

    overall: Dict[str, Dict[str, Any]] = {}
    for c in conditions:
        subset = [r for r in trials_data if r["condition"] == c]
        tot = len(subset)
        colls = sum(1 for r in subset if r["collision"])
        passes = sum(1 for r in subset if r["passed_door"])
        clearances = [r["min_clearance_m"] for r in subset if r["min_clearance_m"] is not None]

        c_rate, c_low, c_high = wilson_score_interval(colls, tot)
        p_rate, p_low, p_high = wilson_score_interval(passes, tot)
        clear_stats = continuous_ci(clearances)

        overall[c] = {
            "total_runs": tot,
            "collision_count": colls,
            "collision_rate": c_rate,
            "collision_ci_95": [c_low, c_high],
            "pass_count": passes,
            "pass_rate": p_rate,
            "pass_ci_95": [p_low, p_high],
            "min_door_clearance": clear_stats
        }

    summary_payload = {
        "metadata": {
            "n_trials": n,
            "master_seed": seed,
            "door_widths": DOOR_WIDTHS,
            "conditions": conditions
        },
        "overall": overall,
        "by_door_width": by_door_width,
        "waylo_failure_cases": {
            "count": len(waylo_failures),
            "failure_rate": round(len(waylo_failures) / n, 4) if n > 0 else 0.0,
            "cases": waylo_failures
        }
    }

    summary_file = out_path / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    # Print Summary Table
    print("\n" + "=" * 90)
    print(f"{'Door (m)':<10} | {'Condition':<12} | {'Collision Rate (95% CI)':<26} | {'Pass Rate (95% CI)':<26} | {'Mean Clearance':<14}")
    print("-" * 90)
    for w in DOOR_WIDTHS:
        w_str = f"{w:.2f}"
        for c in conditions:
            st = by_door_width[w_str][c]
            c_str = f"{st['collision_rate']*100:5.1f}% [{st['collision_ci_95'][0]*100:4.1f}%, {st['collision_ci_95'][1]*100:4.1f}%]"
            p_str = f"{st['pass_rate']*100:5.1f}% [{st['pass_ci_95'][0]*100:4.1f}%, {st['pass_ci_95'][1]*100:4.1f}%]"
            cl_str = f"{st['min_door_clearance']['mean']:.3f} m"
            print(f"{w_str:<10} | {c:<12} | {c_str:<26} | {p_str:<26} | {cl_str:<14}")
        print("-" * 90)

    print("\nOVERALL SUMMARY:")
    print("-" * 90)
    for c in conditions:
        st = overall[c]
        c_str = f"{st['collision_rate']*100:5.1f}% [{st['collision_ci_95'][0]*100:4.1f}%, {st['collision_ci_95'][1]*100:4.1f}%]"
        p_str = f"{st['pass_rate']*100:5.1f}% [{st['pass_ci_95'][0]*100:4.1f}%, {st['pass_ci_95'][1]*100:4.1f}%]"
        cl_str = f"{st['min_door_clearance']['mean']:.3f} m"
        print(f"{'OVERALL':<10} | {c:<12} | {c_str:<26} | {p_str:<26} | {cl_str:<14}")
    print("=" * 90)

    # Print WAYLO Failure Cases Separately
    print("\n" + "#" * 90)
    print("  WAYLO FAILURE CASES / LIMITATIONS")
    print(f"  Total Failures: {len(waylo_failures)} / {n} runs ({len(waylo_failures)/n*100:.1f}%)")
    print("#" * 90)
    if not waylo_failures:
        print("  None observed in this sample.")
    else:
        for idx, fc in enumerate(waylo_failures, start=1):
            print(f"  [{idx}] Trial #{fc['trial_id']}: Door Width={fc['door_width_m']:.2f}m, "
                  f"Drift={fc['drift_deg']:+.1f} deg, Tremor={fc['tremor_deg']:.1f} deg, "
                  f"Delay={fc['reaction_delay_s']:.2f}s, Fatigue={fc['fatigue_rate']:.3f}, Speed={fc['speed_mps']:.2f}m/s")
            print(f"      Outcome: {fc['reason']} (t={fc['collision_time_s']}s, clearance={fc['min_clearance_m']}m, AEB={fc['aeb_triggered']})")
    print("#" * 90 + "\n")

    print(f"Results saved to:\n  - CSV: {csv_file}\n  - JSON: {summary_file}")
    return summary_payload


def main():
    parser = argparse.ArgumentParser(description="WAYLO Reproducible Monte Carlo Simulation")
    parser.add_argument("--n", type=int, default=100, help="Number of Monte Carlo trials")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--out", type=str, default="data/monte_carlo", help="Output directory")
    args = parser.parse_args()

    run_monte_carlo(n=args.n, seed=args.seed, out_dir=args.out)


if __name__ == "__main__":
    main()
