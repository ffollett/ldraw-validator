from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from validator.catalog import get_part, PART_CATALOG

COMMON_PARTS = [
    "3001", # Brick 2x4 (8 studs)
    "3003", # Brick 2x2 (4 studs)
    "3005", # Brick 1x1 (1 stud)
    "3020", # Plate 2x4 (8 studs)
    "3069b", # Tile 1x2 (0 studs)
]

def main():
    print("Testing dynamic catalog loading...")
    
    for part_id in COMMON_PARTS:
        print(f"\nLoading part {part_id}...")
        try:
            info = get_part(part_id)
            print(f"  Name: {info.name}")
            print(f"  Studs Found: {len(info.studs)}")
            if len(info.studs) > 0:
                # print(f"  First Stud: {info.studs[0]}")
                for s in info.studs:
                    print(f"  Stud: {s}")
            
            # Simple validation
            expected_studs = {
                "3001": 8,
                "3003": 4,
                "3005": 1,
                "3020": 8,
                "3069b": 0
            }
            
            if len(info.studs) == expected_studs[part_id]:
                print("  [PASS] Stud count correct")
            else:
                print(f"  [FAIL] Expected {expected_studs[part_id]} studs, found {len(info.studs)}")
                
        except Exception as e:
            print(f"  [ERROR] Failed to load: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
