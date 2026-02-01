#!/usr/bin/env python
"""
Test rendering of parts with different extraction statuses.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validator.scene_graph import SceneGraph
from validator.parser import Placement
from validator.renderer import render_scene

# Test parts with different statuses
test_cases = [
    ("3001", "partial", "2x4 brick - studs in subfile"),
    ("004845a", "partial", "sticker with geometry"),
    ("004762a", "failed", "sticker - all in subfiles"),
    ("0901", "success", "baseplate with direct studs"),
]

output_dir = Path(__file__).parent.parent / "test_renders"
output_dir.mkdir(exist_ok=True)

print("=" * 60)
print("TESTING RENDERING OF DIFFERENT EXTRACTION STATUSES")
print("=" * 60)

for part_id, expected_status, description in test_cases:
    print(f"\n{part_id} ({expected_status}): {description}")
    
    # Create scene with single part
    sg = SceneGraph()
    sg.add_placement(Placement(
        part_id=part_id,
        color=16,
        position=(0.0, 0.0, 0.0),
        rotation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    ))
    
    # Render
    output_path = output_dir / f"{part_id}.png"
    success = render_scene(sg, str(output_path), width=400, height=400)
    
    if success and output_path.exists():
        size = output_path.stat().st_size
        print(f"  ✓ Rendered successfully ({size:,} bytes)")
    else:
        print(f"  ✗ Rendering failed")

print(f"\n\nOutput directory: {output_dir}")
print("=" * 60)
