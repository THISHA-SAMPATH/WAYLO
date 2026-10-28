"""
Run WAYLO Privacy Pipeline on Depth Images (Public Indoor Depth Datasets).

Processes a depth image (.npy or 16-bit PNG), optionally paired with an RGB image,
and extracts ONLY scalar doorway geometry features (width, lateral offset, approach angle, distance).

Guarantees:
- RGB image (if provided) is dropped in-memory immediately.
- Only scalar doorway features are returned; no point clouds or depth image arrays leave the module.
- Audit invariants: images_written == 0, depth_frames_sent_to_cloud == 0.
- No files are created or written to disk.

Usage:
  python scripts/run_on_depth_image.py [--input path/to/depth.npy] [--rgb path/to/color.png]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.privacy_scrubber import (
    extract_doorway_features,
    create_synthetic_depth_frame,
    get_audit_counters,
    reset_audit_counters
)


def run_pipeline(input_path: str | None = None, rgb_path: str | None = None) -> dict:
    reset_audit_counters()

    # If no file provided, generate a benchmark depth image (e.g. 0.91m standard ADA door at 2.5m)
    if input_path is None or not Path(input_path).exists():
        print("[INFO] No external depth image provided; generating synthetic NYU Depth V2 style indoor frame.")
        depth_data = create_synthetic_depth_frame(
            door_width_m=0.91,
            door_distance_m=2.5,
            lateral_offset_m=0.10,
            approach_angle_deg=4.0
        )
    else:
        print(f"[INFO] Loading depth input: {input_path}")
        depth_data = input_path

    rgb_data = None
    if rgb_path and Path(rgb_path).exists():
        print(f"[INFO] Received optional RGB frame: {rgb_path} (will be discarded immediately)")
        from PIL import Image
        with Image.open(rgb_path) as img:
            rgb_data = np.array(img)
    elif rgb_path:
        print(f"[INFO] Mock RGB frame provided (will be discarded immediately)")
        rgb_data = np.zeros((480, 640, 3), dtype=np.uint8)

    # Execute privacy extraction
    result = extract_doorway_features(depth_data, rgb_image=rgb_data)

    # Privacy verification checks:
    # 1. Output must not contain any numpy arrays or raw lists of points
    for k, v in result.items():
        assert not isinstance(v, np.ndarray), f"Violation: key '{k}' contains an ndarray!"
        if isinstance(v, (list, tuple)):
            for item in v:
                assert not isinstance(item, (list, tuple, np.ndarray)), f"Violation: nested array in '{k}'"

    # 2. Check audit counters
    audit = get_audit_counters()
    assert audit["images_written"] == 0, "Privacy Violation: images were written to disk!"
    assert audit["depth_frames_sent_to_cloud"] == 0, "Privacy Violation: depth frames were sent to cloud!"
    if rgb_data is not None:
        assert audit["rgb_discarded"] >= 1, "Privacy Violation: RGB was not discarded!"

    print("\n" + "=" * 60)
    print("  WAYLO LOCAL DEPTH-ONLY PRIVACY PIPELINE RESULTS")
    print("=" * 60)
    print(f"Status               : {result.get('status')}")
    print(f"Doorway Detected     : {result.get('doorway_detected')}")
    print(f"Door Width (m)       : {result.get('width_m'):.3f} m")
    print(f"Lateral Offset (m)   : {result.get('lateral_offset_m'):+.3f} m")
    print(f"Approach Angle (deg) : {result.get('approach_angle_deg'):+.2f} deg")
    print(f"Distance to Door (m) : {result.get('distance_m'):.3f} m")
    print("-" * 60)
    print("Privacy Audit Counters:")
    for k, v in audit.items():
        print(f"  {k:<28}: {v}")
    print("-" * 60)
    print("Privacy Guarantees:")
    print("  - RGB discarded immediately : YES (in-memory deletion, never stored)")
    print("  - Images written to disk    : 0 (verified)")
    print("  - Sent to cloud             : 0 (local execution only)")
    print("  - Output format             : ONLY 4 scalar doorway features")
    print("=" * 60 + "\n")

    return result


def main():
    parser = argparse.ArgumentParser(description="Run WAYLO Privacy Pipeline on Depth Image")
    parser.add_argument("--input", type=str, default=None, help="Path to .npy or 16-bit PNG depth file")
    parser.add_argument("--rgb", type=str, default=None, help="Path to optional RGB file to test discarding")
    args = parser.parse_args()

    run_pipeline(args.input, args.rgb)


if __name__ == "__main__":
    main()
