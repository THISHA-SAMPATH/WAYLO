"""
Reproducible Monte Carlo Simulation and Sensitivity Sweep for WAYLO Shared-Autonomy Wheelchair Copilot.

Evaluates 3 experimental conditions across randomized doorway scenarios:
1. 'uncorrected': Open-loop driver with constant heading drift and tremor.
2. 'corrective': Closed-loop human driver with visual feedback, reaction delay (0.2-0.6s),
   hand tremor, joystick noise, and fatigue accumulating over time.
3. 'waylo': Corrective human driver assisted by WAYLO shared-autonomy copilot (local perception + dynamic alpha arbitration).

CLI Args:
  --n: Number of randomized trials (default: 1000)
  --seed: Master random seed for reproducibility (default: 42)
  --out: Output directory for runs.csv, summary.json, sensitivity.csv (default: data/monte_carlo)
  --skip-sweep: Skip sensitivity sweep if only running main Monte Carlo
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


def run_monte_carlo(n: int = 1000, seed: int = 42, out_dir: str = "data/monte_carlo") -> Dict[str, Any]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)

    trials_data: List[Dict[str, Any]] = []
    waylo_failures: List[Dict[str, Any]] = []

    print(f"=================================================================")
    print(f"  WAYLO REPRODUCIBLE MONTE CARLO (N={n}, Seed={seed})")
    print(f"  Speeds: 0.60 to 1.20 m/s | Drift: -25.0 to +25.0 deg")
    print(f"  LiDAR Noise: sigma=0.02m, Dropouts=2.0%, Latency=0.10s")
    print(f"=================================================================")

    # Run simulations
    for trial_idx in range(n):
        trial_seed = int(rng.integers(0, 10_000_000))
        trial_rng = np.random.default_rng(trial_seed)

        door_width = float(trial_rng.choice(DOOR_WIDTHS))
        drift = float(trial_rng.uniform(-25.0, 25.0))
        tremor = float(trial_rng.uniform(0.5, 3.5))
        delay = float(trial_rng.uniform(0.2, 0.6))
        fatigue = float(trial_rng.uniform(0.02, 0.08))
        speed = float(trial_rng.uniform(0.6, 1.2))
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
    # Note: As per audit requirement 6, min clearance is reported strictly for passed runs only
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
            # Passed runs only for clearance calculation
            passed_clearances = [
                r["min_clearance_m"] for r in subset
                if r["passed_door"] and not r["collision"] and r["min_clearance_m"] is not None
            ]

            c_rate, c_low, c_high = wilson_score_interval(colls, tot)
            p_rate, p_low, p_high = wilson_score_interval(passes, tot)
            clear_stats = continuous_ci(passed_clearances)

            by_door_width[w_str][c] = {
                "total_runs": tot,
                "collision_count": colls,
                "collision_rate": c_rate,
                "collision_ci_95": [c_low, c_high],
                "pass_count": passes,
                "pass_rate": p_rate,
                "pass_ci_95": [p_low, p_high],
                "min_door_clearance_passed_only": clear_stats
            }

    overall: Dict[str, Dict[str, Any]] = {}
    for c in conditions:
        subset = [r for r in trials_data if r["condition"] == c]
        tot = len(subset)
        colls = sum(1 for r in subset if r["collision"])
        passes = sum(1 for r in subset if r["passed_door"])
        passed_clearances = [
            r["min_clearance_m"] for r in subset
            if r["passed_door"] and not r["collision"] and r["min_clearance_m"] is not None
        ]

        c_rate, c_low, c_high = wilson_score_interval(colls, tot)
        p_rate, p_low, p_high = wilson_score_interval(passes, tot)
        clear_stats = continuous_ci(passed_clearances)

        overall[c] = {
            "total_runs": tot,
            "collision_count": colls,
            "collision_rate": c_rate,
            "collision_ci_95": [c_low, c_high],
            "pass_count": passes,
            "pass_rate": p_rate,
            "pass_ci_95": [p_low, p_high],
            "min_door_clearance_passed_only": clear_stats
        }

    summary_payload = {
        "metadata": {
            "n_trials": n,
            "master_seed": seed,
            "speed_range_mps": [0.60, 1.20],
            "drift_range_deg": [-25.0, 25.0],
            "sensor_noise": {
                "lidar_sigma_m": 0.02,
                "dropout_prob": 0.02,
                "sensor_latency_s": 0.10
            },
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
    print("\n" + "=" * 98)
    print(f"{'Door (m)':<10} | {'Condition':<12} | {'Collision Rate (95% CI)':<26} | {'Pass Rate (95% CI)':<26} | {'Min Clearance (Passed)':<22}")
    print("-" * 98)
    for w in DOOR_WIDTHS:
        w_str = f"{w:.2f}"
        for c in conditions:
            st = by_door_width[w_str][c]
            c_str = f"{st['collision_rate']*100:5.1f}% [{st['collision_ci_95'][0]*100:4.1f}%, {st['collision_ci_95'][1]*100:4.1f}%]"
            p_str = f"{st['pass_rate']*100:5.1f}% [{st['pass_ci_95'][0]*100:4.1f}%, {st['pass_ci_95'][1]*100:4.1f}%]"
            cnt = st['min_door_clearance_passed_only']['count']
            if cnt > 0:
                cl_str = f"{st['min_door_clearance_passed_only']['mean']:.3f} m (N={cnt})"
            else:
                cl_str = "N/A (0 passed)"
            print(f"{w_str:<10} | {c:<12} | {c_str:<26} | {p_str:<26} | {cl_str:<22}")
        print("-" * 98)

    print("\nOVERALL SUMMARY:")
    print("-" * 98)
    for c in conditions:
        st = overall[c]
        c_str = f"{st['collision_rate']*100:5.1f}% [{st['collision_ci_95'][0]*100:4.1f}%, {st['collision_ci_95'][1]*100:4.1f}%]"
        p_str = f"{st['pass_rate']*100:5.1f}% [{st['pass_ci_95'][0]*100:4.1f}%, {st['pass_ci_95'][1]*100:4.1f}%]"
        cnt = st['min_door_clearance_passed_only']['count']
        if cnt > 0:
            cl_str = f"{st['min_door_clearance_passed_only']['mean']:.3f} m (N={cnt})"
        else:
            cl_str = "N/A (0 passed)"
        print(f"{'OVERALL':<10} | {c:<12} | {c_str:<26} | {p_str:<26} | {cl_str:<22}")
    print("=" * 98)

    # Print WAYLO Failure Cases Separately
    print("\n" + "#" * 98)
    print("  WAYLO FAILURE CASES / LIMITATIONS")
    print(f"  Total Failures: {len(waylo_failures)} / {n} runs ({len(waylo_failures)/n*100:.2f}%)")
    print("#" * 98)
    if not waylo_failures:
        print("  None observed in this sample.")
    else:
        for idx, fc in enumerate(waylo_failures, start=1):
            print(f"  [{idx}] Trial #{fc['trial_id']}: Door Width={fc['door_width_m']:.2f}m, "
                  f"Drift={fc['drift_deg']:+.1f} deg, Tremor={fc['tremor_deg']:.1f} deg, "
                  f"Delay={fc['reaction_delay_s']:.2f}s, Fatigue={fc['fatigue_rate']:.3f}, Speed={fc['speed_mps']:.2f}m/s")
            print(f"      Outcome: {fc['reason']} (t={fc['collision_time_s']}s, clearance={fc['min_clearance_m']}m, AEB={fc['aeb_triggered']})")
    print("#" * 98 + "\n")

    print(f"Results saved to:\n  - CSV: {csv_file}\n  - JSON: {summary_file}")
    return summary_payload


def run_sensitivity_sweep(out_dir: str = "data/monte_carlo", seed: int = 42,
                          trials_per_setting: int = 50) -> List[Dict[str, Any]]:
    """
    Audit requirement 4: Sensitivity sweep varying reaction delay, visual gain,
    tremor, and fatigue over plausible physiological ranges.
    Compares WAYLO vs Corrective baseline across randomized door widths and drifts.
    Saves results to data/monte_carlo/sensitivity.csv.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    sweep_file = out_path / "sensitivity.csv"

    print("\n" + "=" * 98)
    print("  RUNNING PHYSIOLOGICAL SENSITIVITY SWEEP (WAYLO vs CORRECTIVE BASELINE)")
    print("=" * 98)

    param_sweeps = {
        "reaction_delay_s": [0.15, 0.25, 0.35, 0.50, 0.65],
        "visual_gain": [0.6, 0.9, 1.2, 1.5, 1.8],
        "tremor_deg": [0.5, 1.5, 2.5, 3.5, 4.5],
        "fatigue_rate": [0.01, 0.03, 0.05, 0.07, 0.10]
    }

    # Baseline nominal values
    nominal = {
        "reaction_delay_s": 0.35,
        "visual_gain": 1.2,
        "tremor_deg": 2.0,
        "fatigue_rate": 0.05,
        "joystick_noise_deg": 1.0
    }

    rng = np.random.default_rng(seed)
    sweep_rows: List[Dict[str, Any]] = []

    for param_name, param_values in param_sweeps.items():
        print(f"\n--- Sweeping Parameter: {param_name} across {param_values} ---")
        for val in param_values:
            corr_colls, corr_passes, corr_clears = 0, 0, []
            waylo_colls, waylo_passes, waylo_clears = 0, 0, []

            for t_idx in range(trials_per_setting):
                t_seed = int(rng.integers(0, 10_000_000))
                t_rng = np.random.default_rng(t_seed)

                dw = float(t_rng.choice(DOOR_WIDTHS))
                drift = float(t_rng.uniform(-25.0, 25.0))
                speed = float(t_rng.uniform(0.6, 1.2))

                # Build trial parameters with sweep override
                p = dict(nominal)
                p[param_name] = val
                p.update({
                    "drift_deg": drift,
                    "speed_mps": speed,
                    "door_width_m": dw,
                    "seed": t_seed
                })

                # Run corrective and waylo
                res_corr = sim.run("corrective", **p)
                res_waylo = sim.run("waylo", **p)

                # Corrective metrics
                s_c = res_corr["summary"]
                if s_c["collision"]:
                    corr_colls += 1
                if s_c["passed_door"]:
                    corr_passes += 1
                    if s_c["min_door_clearance_m"] is not None and not s_c["collision"]:
                        corr_clears.append(s_c["min_door_clearance_m"])

                # WAYLO metrics
                s_w = res_waylo["summary"]
                if s_w["collision"]:
                    waylo_colls += 1
                if s_w["passed_door"]:
                    waylo_passes += 1
                    if s_w["min_door_clearance_m"] is not None and not s_w["collision"]:
                        waylo_clears.append(s_w["min_door_clearance_m"])

            # Compute statistics for corrective
            c_rate, c_low, c_high = wilson_score_interval(corr_colls, trials_per_setting)
            p_rate, p_low, p_high = wilson_score_interval(corr_passes, trials_per_setting)
            mean_clr_c = float(np.mean(corr_clears)) if corr_clears else 0.0

            sweep_rows.append({
                "parameter": param_name,
                "param_value": val,
                "condition": "corrective",
                "trials": trials_per_setting,
                "collision_count": corr_colls,
                "collision_rate": c_rate,
                "collision_ci_lower": c_low,
                "collision_ci_upper": c_high,
                "pass_count": corr_passes,
                "pass_rate": p_rate,
                "pass_ci_lower": p_low,
                "pass_ci_upper": p_high,
                "min_clearance_passed_mean": round(mean_clr_c, 4)
            })

            # Compute statistics for waylo
            wc_rate, wc_low, wc_high = wilson_score_interval(waylo_colls, trials_per_setting)
            wp_rate, wp_low, wp_high = wilson_score_interval(waylo_passes, trials_per_setting)
            mean_clr_w = float(np.mean(waylo_clears)) if waylo_clears else 0.0

            sweep_rows.append({
                "parameter": param_name,
                "param_value": val,
                "condition": "waylo",
                "trials": trials_per_setting,
                "collision_count": waylo_colls,
                "collision_rate": wc_rate,
                "collision_ci_lower": wc_low,
                "collision_ci_upper": wc_high,
                "pass_count": waylo_passes,
                "pass_rate": wp_rate,
                "pass_ci_lower": wp_low,
                "pass_ci_upper": wp_high,
                "min_clearance_passed_mean": round(mean_clr_w, 4)
            })

            print(f"  {param_name}={val:<5}: Corrective Collisions={c_rate*100:4.1f}% | WAYLO Collisions={wc_rate*100:4.1f}% (Pass Rate={wp_rate*100:4.1f}%)")

    # Write sensitivity.csv
    fieldnames = list(sweep_rows[0].keys())
    with open(sweep_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sweep_rows)

    print("\n" + "=" * 98)
    print(f"  Sensitivity sweep complete. Saved to: {sweep_file}")
    print("=" * 98)
    return sweep_rows


def main():
    parser = argparse.ArgumentParser(description="WAYLO Reproducible Monte Carlo Simulation and Sensitivity Sweep")
    parser.add_argument("--n", type=int, default=1000, help="Number of Monte Carlo trials (default: 1000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--out", type=str, default="data/monte_carlo", help="Output directory")
    parser.add_argument("--skip-sweep", action="store_true", help="Skip physiological sensitivity sweep")
    args = parser.parse_args()

    run_monte_carlo(n=args.n, seed=args.seed, out_dir=args.out)

    if not args.skip_sweep:
        run_sensitivity_sweep(out_dir=args.out, seed=args.seed, trials_per_setting=50)


if __name__ == "__main__":
    main()
