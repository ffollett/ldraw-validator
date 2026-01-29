from dataclasses import dataclass
from typing import Optional
import json
from pathlib import Path


@dataclass
class Placement:
    part_id: str
    color: int
    x: float
    y: float
    z: float
    rotation: tuple[float, ...] = (1, 0, 0, 0, 1, 0, 0, 0, 1)
    
    def to_ldraw_line(self) -> str:
        r = self.rotation
        return f"1 {self.color} {self.x} {self.y} {self.z} {r[0]} {r[1]} {r[2]} {r[3]} {r[4]} {r[5]} {r[6]} {r[7]} {r[8]} {self.part_id}.dat"


@dataclass 
class TestCase:
    id: str
    name: str
    description: str
    placements: list[Placement]
    expected_valid: bool
    expected_errors: Optional[list[dict]] = None
    submodels: Optional[dict[str, list[Placement]]] = None
    
    def to_ldraw(self) -> str:
        lines = []
        if self.submodels:
            # Main model first so loader picks it up as root
            lines.append(f"0 FILE main.ldr")
            lines.extend(p.to_ldraw_line() for p in self.placements)
            lines.append("0 NOFILE")
            
            for name, places in self.submodels.items():
                lines.append(f"0 FILE {name}.ldr")
                lines.extend(p.to_ldraw_line() for p in places)
                lines.append("0 NOFILE")
        else:
            lines.append(f"0 {self.name}")
            lines.extend(p.to_ldraw_line() for p in self.placements)
        return "\n".join(lines)
    
    def to_manifest_entry(self, file_path: str) -> dict:
        entry = {
            "id": self.id,
            "file": file_path,
            "expected_valid": self.expected_valid,
            "description": self.description,
        }
        if self.expected_errors:
            entry["expected_errors"] = self.expected_errors
        return entry


# Constants
BRICK_HEIGHT = 24
PLATE_HEIGHT = 8
STUD_SPACING = 20

# Common parts
BRICK_2X4 = "3001"
BRICK_2X2 = "3003"
BRICK_1X1 = "3005"
PLATE_2X4 = "3020"
TILE_1X2 = "3069b"


# Define test cases
TEST_CASES = [
    # Valid cases
    TestCase(
        id="1.1",
        name="Stacked bricks",
        description="Basic stud-to-antistud connection test",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X4, 15, 0, -48, 0),
        ],
        expected_valid=True,
    ),
    TestCase(
        id="1.2",
        name="Two bricks side by side",
        description="Two grounded bricks not connected to each other",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X4, 15, 80, -24, 0),
        ],
        expected_valid=True,
    ),
    TestCase(
        id="1.3",
        name="Plate on brick",
        description="Tests plate height handling",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(PLATE_2X4, 15, 0, -32, 0),
        ],
        expected_valid=True,
    ),
    TestCase(
        id="1.4",
        name="Rotated brick connection",
        description="90-degree rotated brick connecting to another",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X4, 15, 20, -48, 0, rotation=(0, 0, 1, 0, 1, 0, -1, 0, 0)),
        ],
        expected_valid=True,
    ),
    TestCase(
        id="1.5",
        name="Offset brick connection",
        description="Brick with partial stud overlap",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X4, 15, 20, -48, 0),
        ],
        expected_valid=True,
    ),
    
    # Invalid cases
    TestCase(
        id="2.1",
        name="Floating brick",
        description="Single brick not connected to anything",
        placements=[
            Placement(BRICK_2X4, 4, 0, -100, 0),
        ],
        expected_valid=False,
        expected_errors=[{"type": "ungrounded", "brick_index": 0}],
    ),
    TestCase(
        id="2.2",
        name="Floating assembly",
        description="Two connected bricks that are both floating",
        placements=[
            Placement(BRICK_2X4, 4, 0, -100, 0),
            Placement(BRICK_2X4, 15, 0, -124, 0),
        ],
        expected_valid=False,
        expected_errors=[
            {"type": "ungrounded", "brick_index": 0},
            {"type": "ungrounded", "brick_index": 1},
        ],
    ),
    TestCase(
        id="2.3",
        name="Collision - identical positions",
        description="Two bricks at the exact same position",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X4, 15, 0, -24, 0),
        ],
        expected_valid=False,
        expected_errors=[{"type": "collision", "brick_indices": [0, 1]}],
    ),
    TestCase(
        id="2.4",
        name="Collision - partial intersection",
        description="Two bricks partially overlapping illegally",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X4, 15, 10, -24, 0),
        ],
        expected_valid=False,
        expected_errors=[{"type": "collision", "brick_indices": [0, 1]}],
    ),
    TestCase(
        id="2.5",
        name="Near miss",
        description="Brick positioned close but studs don't align",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X4, 15, 10, -48, 0),
        ],
        expected_valid=False,
        expected_errors=[{"type": "ungrounded", "brick_index": 1}],
    ),
    TestCase(
        id="2.6",
        name="Gap between bricks",
        description="Bricks aligned but with vertical gap",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X4, 15, 0, -50, 0),
        ],
        expected_valid=False,
        expected_errors=[{"type": "ungrounded", "brick_index": 1}],
    ),
    TestCase(
        id="2.7",
        name="Vertical intersection",
        description="Bricks aligned but intersecting vertically",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X4, 15, 0, -40, 0),
        ],
        expected_valid=False,
        expected_errors=[{"type": "collision", "brick_indices": [0, 1]}],
    ),
    TestCase(
        id="2.8",
        name="Grid mismatch rotation",
        description="Rotated brick with grid mismatch",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X4, 15, 30, -48, 0, rotation=(0,0,1,0,1,0,-1,0,0)), # No Z match
        ],
        expected_valid=False,
        expected_errors=[{"type": "ungrounded", "brick_index": 1}],
    ),
    TestCase(
        id="2.9",
        name="Offset misalignment",
        description="Tile with Z-axis misalignment",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(TILE_1X2, 15, 20, -32, 0), 
        ],
        expected_valid=False,
        expected_errors=[{"type": "ungrounded", "brick_index": 1}],
    ),
    TestCase(
        id="2.10",
        name="Near grid miss",
        description="Brick off by 5 LDU",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X4, 15, 5, -48, 0),
        ],
        expected_valid=False,
        expected_errors=[{"type": "grid_alignment", "brick_index": 1}],
    ),
    
    # Edge cases
    TestCase(
        id="3.1",
        name="Tile on brick",
        description="Tile element covering studs",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(TILE_1X2, 15, 20, -32, 10), 
        ],
        expected_valid=True,
    ),
    TestCase(
        id="3.2",
        name="Ten brick stack",
        description="Tall stack testing connection chaining",
        placements=[
            Placement(BRICK_2X4, color, 0, -24 - (i * 24), 0)
            for i, color in enumerate([4, 15, 14, 1, 2, 3, 5, 6, 7, 8])
        ],
        expected_valid=True,
    ),
    TestCase(
        id="3.3",
        name="Branching structure",
        description="One brick supporting two others",
        placements=[
            Placement(BRICK_2X4, 4, 0, -24, 0),
            Placement(BRICK_2X2, 15, -20, -48, 0),
            Placement(BRICK_2X2, 14, 40, -48, 0),
        ],
        expected_valid=True,
    ),
    
    # Complex MPD cases
    TestCase(
        id="4.1",
        name="MPD Rotated Submodel",
        description="Submodel is rotated 90deg, world coordinates should still align for connection",
        submodels={
            "sub": [
                # In submodel, brick is at 0, 0, 0
                Placement(BRICK_2X4, 4, 0, 0, 0)
            ]
        },
        placements=[
            # Base brick
            Placement(BRICK_2X4, 1, 0, -24, 0),
            # Place 'sub' rotated 90deg around Y
            # Rotation matrix for 90deg around Y: (0, 0, 1, 0, 1, 0, -1, 0, 0)
            # Position it at (20, -48, 0) to align studs
            Placement("sub", 4, 20, -48, 0, rotation=(0, 0, 1, 0, 1, 0, -1, 0, 0))
        ],
        expected_valid=True,
    ),
    TestCase(
        id="4.2",
        name="MPD Collision in Submodel",
        description="Two bricks in a submodel overlap",
        submodels={
            "col_sub": [
                Placement(BRICK_2X4, 4, 0, 0, 0),
                Placement(BRICK_2X4, 1, 10, 0, 0) # Collision
            ]
        },
        placements=[
            Placement("col_sub", 15, 0, -24, 0)
        ],
        expected_valid=False,
        expected_errors=[{"type": "collision", "brick_indices": [0, 1]}]
    ),
    TestCase(
        id="4.3",
        name="MPD Floating in Submodel",
        description="One brick in submodel is floating",
        submodels={
            "float_sub": [
                Placement(BRICK_2X4, 4, 0, 0, 0), # Connected to ground when placed at Y=-24
                Placement(BRICK_2X4, 1, 0, -100, 0) # Floating
            ]
        },
        placements=[
            Placement("float_sub", 15, 0, -24, 0)
        ],
        expected_valid=False,
        expected_errors=[{"type": "ungrounded", "brick_index": 1}]
    )
]


def generate_test_data(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    valid_dir = output_dir / "valid"
    invalid_dir = output_dir / "invalid"
    edge_dir = output_dir / "edge_cases"
    
    for d in [valid_dir, invalid_dir, edge_dir]:
        d.mkdir(exist_ok=True)
    
    manifest_entries = []
    
    for case in TEST_CASES:
        if case.id.startswith("1."):
            subdir = "valid"
            target_dir = valid_dir
        elif case.id.startswith("2."):
            subdir = "invalid"
            target_dir = invalid_dir
        elif case.id.startswith("3."):
            subdir = "edge_cases"
            target_dir = edge_dir
        else: # 4.x
            subdir = "edge_cases"
            target_dir = edge_dir
        
        filename = f"{case.id}_{case.name.lower().replace(' ', '_').replace('-', '_')}.ldr"
        file_path = target_dir / filename
        
        file_path.write_text(case.to_ldraw())
        
        relative_path = f"{subdir}/{filename}"
        manifest_entries.append(case.to_manifest_entry(relative_path))
    
    manifest = {"test_cases": manifest_entries}
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    
    print(f"Generated {len(TEST_CASES)} test cases in {output_dir}")


if __name__ == "__main__":
    generate_test_data(Path("test_data"))