from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from validator.scene_graph import SceneGraph
from validator.loader import Loader
from validator.catalog_db import get_part
from validator.geometry import get_world_studs, get_world_antistuds
from validator.connections import studs_connect

def debug_connection():
    file_path = Path("test_data/valid/1.1_stacked_bricks.ldr")
    sg = SceneGraph()
    loader = Loader(sg)
    loader.load(file_path)
    
    p0 = sg.get_placement(0)
    p1 = sg.get_placement(1)
    
    print(f"\nPart 0: {p0.part_id} at {p0.position}")
    print(f"Part 1: {p1.part_id} at {p1.position}")
    
    info0 = get_part(p0.part_id)
    info1 = get_part(p1.part_id)
    
    studs0 = get_world_studs(p0, info0)
    antistuds0 = get_world_antistuds(p0, info0)
    
    studs1 = get_world_studs(p1, info1)
    antistuds1 = get_world_antistuds(p1, info1)
    
    print(f"\nPart 0 Studs (first 3): {studs0[:3]}")
    print(f"Part 0 AntiStuds (first 3): {antistuds0[:3]}")
    
    print(f"\nPart 1 Studs (first 3): {studs1[:3]}")
    print(f"Part 1 AntiStuds (first 3): {antistuds1[:3]}")
    
    # Check for connection between Studs 0 and AntiStuds 1
    print("\nChecking P0 Studs -> P1 AntiStuds:")
    connected = False
    for s in studs0:
        for a in antistuds1:
            if studs_connect(s, a, tolerance=2.0): # Relaxed tolerance for debug
                print(f"  MATCH! Stud {s} - Anti {a}")
                connected = True
                break
        if connected: break
        
    if not connected:
        print("  NO MATCH FOUND.")
        # Print closest pair
        min_dist = 9999
        closest = None
        for s in studs0:
            for a in antistuds1:
                dist = sum((x-y)**2 for x,y in zip(s,a))**0.5
                if dist < min_dist:
                    min_dist = dist
                    closest = (s, a)
        print(f"  Closest pair: {closest} Dist: {min_dist}")

if __name__ == "__main__":
    debug_connection()
