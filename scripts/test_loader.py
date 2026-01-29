from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from validator.scene_graph import SceneGraph
from validator.loader import Loader

def test_loader():
    file_path = Path("test_data/mpd_test.ldr")
    sg = SceneGraph()
    loader = Loader(sg)
    
    print(f"Loading {file_path}...")
    loader.load(file_path)
    
    print(f"Scene Graph has {len(sg)} placements.")
    
    if len(sg) != 1:
        print("[FAIL] Expected 1 placement")
        return

    p = sg.get_placement(0)
    print(f"Placement 0: {p.part_id} at {p.position}")
    
    # Expected: 100 + 10 = 110
    if p.part_id == "3001" and p.position[0] == 110.0:
        print("[PASS] Coordinate transformation correct")
    else:
        print(f"[FAIL] Expected 3001 at (110,0,0), got {p.part_id} at {p.position}")

if __name__ == "__main__":
    test_loader()
