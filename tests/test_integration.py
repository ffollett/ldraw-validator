import pytest
from pathlib import Path

from validator import validate_moc, ValidationResult


class TestValidMOCs:
    """All valid test cases should pass validation."""
    
    @pytest.mark.parametrize("case_id", [
        "1.1", "1.2", "1.3", "1.4", "1.5",  # Basic valid
        "3.1", "3.2", "3.3",          # Edge cases (valid)
    ])
    def test_valid_case(self, case_id: str, manifest: dict, test_data_dir: Path):
        case = next(c for c in manifest["test_cases"] if c["id"] == case_id)
        file_path = test_data_dir / case["file"]
        
        result = validate_moc(file_path)
        
        assert result.is_valid, (
            f"Case {case_id} ({case['description']}) should be valid.\n"
            f"Errors: {result.errors}"
        )


class TestInvalidMOCs:
    """All invalid test cases should fail with correct error types."""
    
    @pytest.mark.parametrize("case_id,expected_error_type", [
        ("2.1", "ungrounded"),
        ("2.2", "ungrounded"),
        ("2.3", "collision"),
        ("2.4", "collision"),
        ("2.5", "ungrounded"),
        ("2.6", "ungrounded"),
        ("2.7", "collision"),
        ("2.8", "ungrounded"),
        ("2.9", "ungrounded"),
        ("2.10", "grid_alignment"),
    ])
    def test_invalid_case(
        self, 
        case_id: str, 
        expected_error_type: str,
        manifest: dict, 
        test_data_dir: Path
    ):
        case = next(c for c in manifest["test_cases"] if c["id"] == case_id)
        file_path = test_data_dir / case["file"]
        
        result = validate_moc(file_path)
        
        assert not result.is_valid, (
            f"Case {case_id} ({case['description']}) should be invalid."
        )
        
        error_types = [e.error_type for e in result.errors]
        assert expected_error_type in error_types, (
            f"Case {case_id} should have error type '{expected_error_type}'.\n"
            f"Actual errors: {result.errors}"
        )



# Unit logic has been moved to:
# - tests/test_parser.py
# - tests/test_connections.py
# - tests/test_grounding.py
