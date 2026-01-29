from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from validator.parser import parse_mpd

def test_mpd_parsing():
    file_path = Path("test_data/mpd_test.ldr")
    if not file_path.exists():
        print("Test file not found!")
        return

    models = parse_mpd(file_path)
    print(f"Found {len(models)} models: {list(models.keys())}")
    
    if "main.ldr" in models and "submodel.ldr" in models:
        print("[PASS] Found both models")
    else:
        print("[FAIL] Missing models")
        
    main = models["main.ldr"]
    if len(main.placements) == 1 and main.placements[0].part_id == "submodel":
        print("[PASS] Main model correct")
    else:
        print(f"[FAIL] Main model placements: {main.placements}")

    sub = models["submodel.ldr"]
    if len(sub.placements) == 1 and sub.placements[0].part_id == "3001":
        print("[PASS] Submodel correct")
    else:
        print(f"[FAIL] Submodel placements: {sub.placements}")

if __name__ == "__main__":
    test_mpd_parsing()
