"""
Render all test cases with pass/fail badges in filenames.

Usage:
    python scripts/visualize_tests.py
    
Output:
    test_renders/
        ✓_1.1_stacked_bricks.png
        ✗_2.1_floating_brick.png
        ...
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validator import validate_moc
from validator.renderer import render_scene
from validator.scene_graph import SceneGraph
from validator.loader import Loader


def render_test_case(ldr_path, output_path, expected_valid):
    """
    Render a test case and validate it.
    
    Returns:
        (is_correct, actual_valid, errors)
    """
    # Load scene
    sg = SceneGraph()
    loader = Loader(sg)
    
    try:
        loader.load(ldr_path)
    except Exception as e:
        print(f"    ERROR loading: {e}")
        return False, False, [str(e)]
    
    # Render image
    try:
        render_scene(sg, str(output_path), silent_errors=True)
    except Exception as e:
        print(f"    WARNING: Render failed: {e}")
        # Continue anyway - we still want validation results
    
    # Validate
    try:
        result = validate_moc(ldr_path)
        actual_valid = result.is_valid
        errors = [f"{e.error_type}: {e.message}" for e in result.errors]
        
        # Check if result matches expectation
        is_correct = (expected_valid == actual_valid)
        
        return is_correct, actual_valid, errors
    except Exception as e:
        print(f"    ERROR validating: {e}")
        return False, False, [str(e)]


def main():
    project_root = Path(__file__).parent.parent
    test_data_dir = project_root / "test_data"
    output_dir = project_root / "test_renders"
    output_dir.mkdir(exist_ok=True)
    
    # Load manifest
    manifest_path = test_data_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}")
        return
    
    manifest = json.loads(manifest_path.read_text())
    
    log_path = output_dir / "visualize_tests.log"
    with open(log_path, 'w', encoding='utf-8') as log_f:
        def log_print(msg=""):
            print(msg)
            log_f.write(str(msg) + "\n")
            log_f.flush()

        log_print(f"Rendering {len(manifest['test_cases'])} test cases...")
        log_print(f"Output directory: {output_dir}\n")
        
        passed = 0
        failed = 0
        
        for case in manifest["test_cases"]:
            ldr_path = test_data_dir / case["file"]
            
            if not ldr_path.exists():
                log_print(f"✗ {case['id']}: File not found: {ldr_path}")
                failed += 1
                continue
            
            expected_valid = case["expected_valid"]
            
            # Create output filename with badge
            base_name = ldr_path.stem
            
            # Check for existing renders for this test case (any badge)
            existing_renders = list(output_dir.glob(f"*_{case['id']}_*.png"))
            was_overwritten = len(existing_renders) > 0
            for f in existing_renders:
                try:
                    f.unlink()
                except Exception as e:
                    log_print(f"    WARNING: Could not delete existing file {f.name}: {e}")
            
            # Render first to determine pass/fail
            is_correct, actual_valid, errors = render_test_case(
                ldr_path,
                output_dir / f"temp_{base_name}.png",  # Temp name
                expected_valid
            )
            
            # Rename with correct badge
            badge = "✓" if is_correct else "✗"
            final_name = f"{badge}_{case['id']}_{base_name}.png"
            final_path = output_dir / final_name
            
            # Rename temp file to final name
            temp_path = output_dir / f"temp_{base_name}.png"
            if temp_path.exists():
                if final_path.exists():
                    temp_path.replace(final_path)
                else:
                    temp_path.rename(final_path)
            
            # Print result
            status = "PASS" if is_correct else "FAIL"
            expected_str = "valid" if expected_valid else "invalid"
            actual_str = "valid" if actual_valid else "invalid"
            
            log_print(f"{badge} {case['id']}: {case['description']}")
            if was_overwritten:
                log_print(f"    Note: Overwrote existing render file(s)")
            log_print(f"    Expected: {expected_str} | Actual: {actual_str} | {status}")
            
            if errors:
                log_print(f"    Errors: {', '.join(errors[:3])}")  # Show first 3
            
            if is_correct:
                passed += 1
            else:
                failed += 1
        
        # Summary
        log_print(f"\n{'='*60}")
        log_print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
        log_print(f"Output: {output_dir}")
        log_print(f"Log file: {log_path}")
        log_print(f"{'='*60}")
        
        # Create simple index.txt (README.txt)
        index_path = output_dir / "README.txt"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("Test Case Renders\n")
            f.write("==================\n\n")
            f.write("Filenames include pass/fail badges:\n")
            f.write("  ✓ = Test behaved as expected\n")
            f.write("  ✗ = Test result didn't match expectation\n\n")
            f.write(f"Results: {passed} passed, {failed} failed\n\n")
            f.write("Files:\n")
            for img in sorted(output_dir.glob("*.png")):
                f.write(f"  {img.name}\n")
        
        log_print(f"\nCreated {index_path}")


if __name__ == "__main__":
    main()
