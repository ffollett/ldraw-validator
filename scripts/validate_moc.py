from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from validator.scene_graph import SceneGraph
from validator.loader import Loader
from validator.connections import build_connection_graph
from validator.grounding import validate_grounding

def validate_file(file_path: Path):
    print(f"\n--- Validating {file_path.name} ---")
    
    # 1. Load Scene
    sg = SceneGraph()
    loader = Loader(sg)
    try:
        loader.load(file_path)
    except Exception as e:
        print(f"[ERROR] Failed to load: {e}")
        return

    print(f"Loaded {len(sg)} parts.")
    
    # 2. Build Connections
    connections = build_connection_graph(sg)
    # print(f"Found {len(connections)} connections.")
    
    # 3. Check Grounding
    is_grounded_val, floating = validate_grounding(sg.placements, connections)
    
    if is_grounded_val:
        print(f"[PASS] {file_path.name}")
    else:
        print(f"[FAIL] {file_path.name} - Floating parts: {floating}")

def main():
    base_dir = Path("test_data")
    
    # Test Valid Cases
    print("\n=== TESTING VALID MODELS ===")
    for p in (base_dir / "valid").glob("*.ldr"):
        validate_file(p)
        
    # Test Invalid Cases
    print("\n=== TESTING INVALID MODELS ===")
    for p in (base_dir / "invalid").glob("*.ldr"):
        validate_file(p)

if __name__ == "__main__":
    main()
