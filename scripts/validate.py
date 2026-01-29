from pathlib import Path
import sys
import argparse

# Add src to path to allow importing the validator package
sys.path.append(str(Path(__file__).parent.parent / "src"))

from validator import validate_moc

def main():
    parser = argparse.ArgumentParser(description="Validate a LEGO LDraw/MPD file.")
    parser.add_argument("file", type=str, help="Path to the .ldr or .mpd file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    args = parser.parse_args()
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist.")
        sys.exit(1)
        
    print(f"Validating {file_path}...")
    result = validate_moc(file_path)
    
    if result.is_valid:
        print(f"✅ PASS: {file_path.name} is valid.")
    else:
        print(f"❌ FAIL: {file_path.name} has {len(result.errors)} errors:")
        for err in result.errors:
            print(f"  - [{err.error_type.upper()}] {err.message}")
            if args.verbose and err.brick_indices:
                print(f"    Affected brick indices: {err.brick_indices}")

if __name__ == "__main__":
    main()
