"""
WAYLO: Assistive Mobility Safety & Independence Ledger.

Records operational telemetry events:
- assist_engaged: Copilot smoothly blends guidance authority (alpha >= 0.10)
- near_miss: Proximity drops below safe safety threshold (clearance < 0.15m) without collision
- scrape: Physical brush/scrape with door jamb or corridor boundary (clearance < 0.04m)
- collision: Chair structure impacts obstacle or wall slab
- human_rescue: Driver takes manual corrective takeover or caregiver intervenes

Calculates real-world clinical and economic metrics:
- independence ratio: Proportion of time / authority where user drove without copilot override
- assisted time: Cumulative time (seconds) where copilot guidance was active
- corrections saved: Frequency of hazardous steering deviations automatically corrected
- estimated repair cost avoided: Facility and hardware damage costs avoided based on
  transparent, configurable assumptions (clearly labeled as assumptions).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union
import numpy as np

# Configurable damage repair assumptions (labeled as assumptions)
DEFAULT_COST_ASSUMPTIONS: Dict[str, Any] = {
    "disclaimer": (
        "LABELED AS MODEL ASSUMPTIONS: Estimated repair cost figures represent configurable "
        "operational heuristics based on published institutional facility maintenance records "
        "(drywall/door-frame repairs: ~$150-$350) and assistive power wheelchair servicing data "
        "(footrest, caster, and motor-hub realignments: ~$500-$1,200)."
    ),
    "scrape_repair_cost_usd": 150.0,
    "collision_repair_cost_usd": 850.0,
    "near_miss_averted_cost_usd": 350.0
}

VALID_EVENT_TYPES = (
    "assist_engaged",
    "near_miss",
    "scrape",
    "collision",
    "human_rescue"
)


class MobilityLedger:
    """In-memory event ledger and clinical metric calculator."""

    def __init__(self, cost_assumptions: Optional[Dict[str, Any]] = None) -> None:
        self.events: List[Dict[str, Any]] = []
        self.total_operating_time_s: float = 0.0
        self.assisted_time_s: float = 0.0
        self.mean_alpha_history: List[float] = []
        self.corrections_saved: int = 0
        self.cost_assumptions: Dict[str, Any] = dict(cost_assumptions or DEFAULT_COST_ASSUMPTIONS)

    def log_event(
        self,
        event_type: str,
        timestamp_s: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Logs a single mobility event to the ledger."""
        evt_type = str(event_type).lower().strip()
        if evt_type not in VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type '{event_type}'. Must be one of: {VALID_EVENT_TYPES}")

        t = timestamp_s if timestamp_s is not None else round(time.time(), 3)
        record = {
            "event_id": len(self.events) + 1,
            "event_type": evt_type,
            "timestamp_s": round(float(t), 3),
            "details": details or {}
        }
        self.events.append(record)
        return record

    def record_sim_run(
        self,
        run_data: Dict[str, Any],
        door_width_m: float = 0.91,
        unassisted_collision: bool = False
    ) -> Dict[str, Any]:
        """
        Processes a full closed-loop simulation trajectory into ledger events and metrics.
        """
        summary = run_data.get("summary", {})
        t_arr = run_data.get("t", [])
        alpha_arr = run_data.get("alpha", [])
        dt = 0.02

        dur = float(summary.get("duration_s", len(t_arr) * dt))
        self.total_operating_time_s += dur

        if len(alpha_arr) > 0:
            alphas = np.array(alpha_arr, dtype=float)
            assisted_mask = alphas >= 0.10
            assisted_steps = int(np.sum(assisted_mask))
            active_assisted_time = round(assisted_steps * dt, 2)
            self.assisted_time_s += active_assisted_time
            self.mean_alpha_history.append(float(np.mean(alphas)))

            # 1. Check if assist was engaged
            if np.any(assisted_mask):
                first_assist_step = int(np.argmax(assisted_mask))
                t_first = float(t_arr[first_assist_step]) if len(t_arr) > first_assist_step else 0.5
                self.log_event("assist_engaged", timestamp_s=t_first, details={
                    "peak_alpha": float(summary.get("peak_alpha", np.max(alphas))),
                    "door_width_m": door_width_m
                })

        # 2. Check collisions
        if summary.get("collision", False):
            self.log_event("collision", timestamp_s=summary.get("collision_time_s", dur), details={
                "door_width_m": door_width_m,
                "duration_s": dur
            })
        else:
            min_c = summary.get("min_door_clearance_m")
            if min_c is not None:
                if min_c < 0.04:
                    self.log_event("scrape", timestamp_s=dur * 0.7, details={
                        "clearance_m": min_c,
                        "door_width_m": door_width_m
                    })
                elif min_c < 0.15:
                    self.log_event("near_miss", timestamp_s=dur * 0.7, details={
                        "clearance_m": min_c,
                        "door_width_m": door_width_m
                    })

        # 3. Corrections saved: an automated intervention that prevented collision or deviation
        if unassisted_collision and not summary.get("collision", False) and summary.get("passed_door", False):
            self.corrections_saved += 1
        elif summary.get("peak_alpha", 0.0) >= 0.35 and not summary.get("collision", False):
            self.corrections_saved += 1

        return self.compute_metrics()

    def compute_metrics(
        self,
        cost_assumptions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculates cumulative independence ratio, assisted time, corrections saved, and cost avoided."""
        assumptions = dict(cost_assumptions or self.cost_assumptions)

        total_t = max(self.total_operating_time_s, 0.001)
        assisted_t = min(self.assisted_time_s, total_t)
        unassisted_t = max(0.0, total_t - assisted_t)

        # Independence ratio by time: proportion of navigation without copilot takeover
        indep_ratio_time = round(unassisted_t / total_t, 3)

        # Independence ratio by authority: 1.0 - mean arbitration alpha
        if self.mean_alpha_history:
            mean_alpha = float(np.mean(self.mean_alpha_history))
            indep_ratio_auth = round(max(0.0, min(1.0, 1.0 - mean_alpha)), 3)
        else:
            indep_ratio_auth = 1.0

        # Event counts
        event_counts = {k: 0 for k in VALID_EVENT_TYPES}
        for e in self.events:
            et = e["event_type"]
            if et in event_counts:
                event_counts[et] += 1

        # Heuristic calculation of repair costs avoided
        collision_cost = float(assumptions.get("collision_repair_cost_usd", 850.0))
        near_miss_cost = float(assumptions.get("near_miss_averted_cost_usd", 350.0))
        scrape_cost = float(assumptions.get("scrape_repair_cost_usd", 150.0))

        # Each saved correction that passed where baseline collided represents an avoided collision
        avoided_cost = (
            (self.corrections_saved * collision_cost) +
            (event_counts["near_miss"] * (near_miss_cost - scrape_cost))
        )
        avoided_cost = round(max(0.0, avoided_cost), 2)

        return {
            "status": "SUCCESS",
            "total_operating_time_s": round(self.total_operating_time_s, 2),
            "assisted_time_s": round(self.assisted_time_s, 2),
            "unassisted_time_s": round(unassisted_t, 2),
            "independence_ratio": indep_ratio_time,
            "independence_ratio_authority": indep_ratio_auth,
            "corrections_saved": self.corrections_saved,
            "event_counts": event_counts,
            "total_events_logged": len(self.events),
            "estimated_repair_cost_avoided_usd": avoided_cost,
            "cost_assumptions": assumptions
        }

    def clear(self) -> None:
        """Clears all logged events and resets metric accumulators."""
        self.events.clear()
        self.total_operating_time_s = 0.0
        self.assisted_time_s = 0.0
        self.mean_alpha_history.clear()
        self.corrections_saved = 0


# Global singleton ledger instance
GLOBAL_LEDGER = MobilityLedger()


def get_global_ledger() -> MobilityLedger:
    return GLOBAL_LEDGER
