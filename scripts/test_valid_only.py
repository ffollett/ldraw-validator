from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from validator.scene_graph import SceneGraph
from validator.loader import Loader
from validator.connections import build_connection_graph
from validator.grounding import validate_grounding

def test_valid_models():
    base_dir = Path("test_data/valid")
    failures = []
    
    print("\n=== VERIFYING VALID MODELS ===")
    for file_path in base_dir.glob("*.ldr"):
        print(f"Testing {file_path.name}...", end=" ")
        
        sg = SceneGraph()
        loader = Loader(sg)
        try:
            loader.load(file_path)
            connections = build_connection_graph(sg)
            is_grounded, floating = validate_grounding(sg.placements, connections)
            
            if is_grounded:
                print("PASS")
            else:
                print(f"FAIL (Floating: {floating})")
                failures.append(file_path.name)
        except Exception as e:
            print(f"ERROR: {e}")
            failures.append(file_path.name)
            
    if not failures:
        print("\n[SUCCESS] All valid models passed.")
    else:
        print(f"\n[FAILURE] {len(failures)} models failed: {failures}")
        sys.exit(1)

if __name__ == "__main__":
    test_valid_models()
