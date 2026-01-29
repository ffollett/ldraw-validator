from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from validator.scene_graph import SceneGraph
from validator.parser import Placement

def test_scene_graph():
    sg = SceneGraph()
    
    # 1. Add some placements
    # 3001 (Brick 2x4) at (0,0,0)
    p1 = Placement(
        part_id="3001",
        color=1,
        position=(0.0, 0.0, 0.0),
        rotation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    )
    id1 = sg.add_placement(p1)
    print(f"Added p1 with ID {id1}")

    # 3001 (Brick 2x4) at (100,0,0) - far away
    p2 = Placement(
        part_id="3001",
        color=4,
        position=(100.0, 0.0, 0.0),
        rotation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    )
    id2 = sg.add_placement(p2)
    print(f"Added p2 with ID {id2}")
    
    # 2. Query point near p1
    # Brick 2x4 is approx 40x24x20 (x,y,z) centered?? 
    # Bounds are x:(-40, 40), y:(-24, 0), z:(-20, 20)
    query_pt = (10.0, -10.0, 0.0)
    print(f"Querying near {query_pt}...")
    results = sg.query_point(query_pt, tolerance=5.0)
    print(f"Results: {results}")
    
    if id1 in results and id2 not in results:
        print("[PASS] Spatial Query 1")
    else:
        print("[FAIL] Spatial Query 1")

    # 3. Query box covering p2
    print("Querying box around p2...")
    results_box = sg.query_box((90, -30, -30), (110, 10, 10))
    print(f"Box Results: {results_box}")
    
    if id2 in results_box and id1 not in results_box:
         print("[PASS] Spatial Query 2")
    else:
        print("[FAIL] Spatial Query 2")

if __name__ == "__main__":
    test_scene_graph()
