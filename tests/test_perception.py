import math

from backend import perception as p


def test_doorway_is_detected_from_the_scan_alone():
    room = p.build_room(1.4)
    scan = p.lidar_scan(room, 0.0, 1.5, 0.0)
    gap = p.detect_gap(scan, 1.5)
    assert gap is not None
    assert abs(gap["center_x"]) < 0.15
    assert abs(gap["width"] - 1.4) < 0.2            # limited by ray spacing
    assert abs(gap["center_y"] - p.DOOR_Y) < 0.05


def test_gap_is_world_fixed_when_the_chair_is_offset_and_rotated():
    room = p.build_room(1.4)
    scan = p.lidar_scan(room, 0.5, 2.0, math.radians(8))
    gap = p.detect_gap(scan, 2.0)
    assert gap is not None
    assert abs(gap["center_x"]) < 0.2                    # door stays at x = 0 in the world frame
    assert gap["center_x"] - 0.5 < -0.3                  # i.e. it lies to the chair's left


def test_front_range_hits_door_wall_when_misaligned():
    room = p.build_room(1.4)
    scan = p.lidar_scan(room, 1.5, 2.0, 0.0)             # straight ahead of the wall, right of the opening
    assert abs(p.front_range(scan) - (p.DOOR_Y - 2.0 - 0.40)) < 0.1


def test_side_clearance_positive_in_open_room():
    left, right = p.side_clearances(p.lidar_scan(p.build_room(), 0.0, 1.0, 0.0))
    assert left > 1.0 and right > 1.0


def test_summary_text_mentions_opening():
    room = p.build_room()
    scan = p.lidar_scan(room, 0.0, 1.5, 0.0)
    assert "Opening detected" in p.scan_summary_text(scan, p.detect_gap(scan, 1.5))
