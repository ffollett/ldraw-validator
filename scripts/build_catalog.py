from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))

from validator.catalog import get_part, save_cache

# List of common parts to pre-populate
COMMON_PARTS = [
    # Bricks
    "3001", "3002", "3003", "3004", "3005", "3006", "3007", "3008", "3009", "3010",
    # Plates
    "3020", "3021", "3022", "3023", "3024", "3710", "3623", "3666", "3460", "3795",
    # Tiles
    "3069b", "3068b", "63864", "2431", "3070b",
    # Slopes
    "3040b", "3039", "3037", "3298", "4445",
]

def build_catalog():
    print(f"Building catalog for {len(COMMON_PARTS)} common parts...")
    
    success_count = 0
    for part_id in COMMON_PARTS:
        try:
            print(f"Processing {part_id}...", end="", flush=True)
            info = get_part(part_id)
            print(f" Done. Found {len(info.studs)} studs.")
            success_count += 1
        except Exception as e:
            print(f" Failed: {e}")
            
    print(f"\nSuccessfully processed {success_count}/{len(COMMON_PARTS)} parts.")
    save_cache()

if __name__ == "__main__":
    build_catalog()
