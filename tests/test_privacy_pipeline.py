import os
from pathlib import Path
import numpy as np
import pytest
from PIL import Image

from backend.privacy_scrubber import (
    extract_doorway_features,
    create_synthetic_depth_frame,
    get_audit_counters,
    reset_audit_counters,
    anonymize_spatial_feed
)


@pytest.fixture(autouse=True)
def clean_audit_counters():
    reset_audit_counters()


def test_no_image_arrays_or_point_clouds_in_output():
    synth = create_synthetic_depth_frame(door_width_m=0.91, door_distance_m=2.5)
    out = extract_doorway_features(synth)

    assert out["status"] == "SUCCESS"
    assert out["doorway_detected"] is True

    # Check that width, lateral offset, approach angle, distance are float scalars
    for key in ["width", "lateral_offset", "approach_angle", "distance"]:
        assert key in out
        assert isinstance(out[key], float)

    # Strictly assert that NO numpy array or point cloud vector exists anywhere in out
    for k, v in out.items():
        assert not isinstance(v, np.ndarray), f"Key '{k}' contains an ndarray!"
        if isinstance(v, (list, tuple)):
            for item in v:
                assert not isinstance(item, (list, tuple, np.ndarray)), f"Key '{k}' contains nested sequence!"


def test_no_files_written_to_disk(tmp_path):
    before_files = set(tmp_path.iterdir())

    synth = create_synthetic_depth_frame(door_width_m=1.0, door_distance_m=3.0)
    dummy_rgb = np.zeros((480, 640, 3), dtype=np.uint8)
    out = extract_doorway_features(synth, rgb_image=dummy_rgb)

    after_files = set(tmp_path.iterdir())
    assert before_files == after_files, "Privacy violation: files were written to disk!"

    audit = get_audit_counters()
    assert audit["images_written"] == 0
    assert audit["depth_frames_sent_to_cloud"] == 0
    assert audit["rgb_discarded"] == 1


def test_rgb_is_immediately_discarded():
    rgb_received = np.ones((100, 100, 3), dtype=np.uint8) * 200
    synth = create_synthetic_depth_frame(door_width_m=0.81, door_distance_m=2.0)

    out = extract_doorway_features(synth, rgb_image=rgb_received)
    audit = get_audit_counters()

    assert audit["rgb_discarded"] == 1
    assert "rgb" not in out
    assert "rgb_image" not in out
    assert "image" not in out


def test_processes_npy_file(tmp_path):
    depth_array = create_synthetic_depth_frame(door_width_m=0.91, door_distance_m=2.2)
    npy_file = tmp_path / "test_depth.npy"
    np.save(npy_file, depth_array)

    out = extract_doorway_features(npy_file)
    assert out["doorway_detected"] is True
    assert abs(out["width_m"] - 0.91) < 0.15
    assert abs(out["distance_m"] - 2.2) < 0.25


def test_processes_16bit_png(tmp_path):
    # 16-bit millimeter depth PNG (standard RealSense / NYU Depth format)
    depth_array = create_synthetic_depth_frame(door_width_m=1.1, door_distance_m=2.8)
    depth_mm = (depth_array * 1000.0).astype(np.uint16)

    png_file = tmp_path / "test_depth_16bit.png"
    Image.fromarray(depth_mm).save(png_file)

    out = extract_doorway_features(png_file)
    assert out["doorway_detected"] is True
    assert abs(out["width_m"] - 1.1) < 0.20
    assert abs(out["distance_m"] - 2.8) < 0.35


def test_backward_compatible_anonymize_spatial_feed():
    out = anonymize_spatial_feed()
    assert out["status"] == "SUCCESS"
    assert "width" in out and "distance" in out
    assert not any(isinstance(v, np.ndarray) for v in out.values())
