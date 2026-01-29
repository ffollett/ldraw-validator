from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from validator.scene_graph import SceneGraph
from validator.loader import Loader
from validator.connections import build_connection_graph
from validator.grounding import validate_grounding
from validator import validate_moc, ValidationResult

def test_invalid_models():
    base_dir = Path("test_data/invalid")
    unexpected_passes = []
    
    print("\n=== VERIFYING INVALID MODELS ===")
    for file_path in base_dir.glob("*.ldr"):
        print(f"Testing {file_path.name}...", end=" ")
        
        # We expect validation to RETURN VALID=False
        result = validate_moc(file_path)
        
        if not result.is_valid:
            error_types = [e.error_type for e in result.errors]
            print(f"FAIL as expected. Errors: {error_types}")
        else:
            print("PASS (Unexpected!)")
            unexpected_passes.append(file_path.name)
            
    if not unexpected_passes:
        print("\n[SUCCESS] All invalid models failed validation.")
    else:
        print(f"\n[FAILURE] {len(unexpected_passes)} invalid models passed: {unexpected_passes}")
        sys.exit(1)

if __name__ == "__main__":
    test_invalid_models()
