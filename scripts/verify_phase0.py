import json
import time
import sys
from pathlib import Path
from validator import validate_moc, ValidationResult, ValidationError

def verify():
    test_data_dir = Path("test_data")
    manifest_path = test_data_dir / "manifest.json"
    
    if not manifest_path.exists():
        print(f"[ERROR] Manifest not found at {manifest_path}")
        sys.exit(1)
        
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
        
    test_cases = manifest.get("test_cases", [])
    total = len(test_cases)
    passed = 0
    failures = []
    
    print(f"Running Phase 0 Verification on {total} test cases...\n")
    print(f"{'ID':<6} {'Name':<30} {'Status':<10} {'Time':<10}")
    print("-" * 60)
    
    overall_start = time.time()
    
    for case in test_cases:
        case_id = case["id"]
        file_rel_path = case["file"]
        expected_valid = case["expected_valid"]
        expected_errors = case.get("expected_errors", [])
        
        file_path = test_data_dir / file_rel_path
        
        start_time = time.time()
        try:
            result = validate_moc(file_path)
        except Exception as e:
            print(f"CRASH in {case_id}: {e}")
            failures.append((case_id, str(e), None))
            continue
            
        duration = time.time() - start_time
        
        case_passed = True
        error_msg = ""
        
        # 1. Check validity
        if result.is_valid != expected_valid:
            case_passed = False
            error_msg += f"ExpValid={expected_valid},Got={result.is_valid}. "
            
        # 2. Check errors
        if not result.is_valid and expected_errors:
            actual_types = [e.error_type for e in result.errors]
            for exp in expected_errors:
                et = exp["type"]
                if et not in actual_types:
                    case_passed = False
                    error_msg += f"Missing {et}. "
        
        if case_passed:
            passed += 1
            print(f"CASE {case_id} OK")
        else:
            print(f"CASE {case_id} FAIL: {error_msg}")
            failures.append((case_id, error_msg, result))

    overall_duration = time.time() - overall_start
    
    print("\n" + "="*60)
    print(f"VERIFICATION SUMMARY")
    print(f"Total Tests:  {total}")
    print(f"Passed:       {passed}")
    print(f"Failed:       {total - passed}")
    print(f"Total Time:   {overall_duration:.2f}s")
    print(f"Avg Time:     {(overall_duration/total)*1000:.2f}ms" if total > 0 else "")
    print("="*60)
    
    if failures:
        print("\nFAILURE DETAILS:")
        for fid, msg, res in failures:
            print(f"[{fid}] {msg}")
            if not res.is_valid:
                print(f"    Actual Errors: {[f'{e.error_type}: {e.message}' for e in res.errors]}")
        sys.exit(1)
    else:
        print("\nAll tests passed successfully!")
        sys.exit(0)

def case_rel_name(path: str) -> str:
    return Path(path).name

if __name__ == "__main__":
    verify()
