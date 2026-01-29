import pytest
import json
from pathlib import Path


@pytest.fixture
def test_data_dir() -> Path:
    return Path(__file__).parent.parent / "test_data"


@pytest.fixture
def manifest(test_data_dir) -> dict:
    manifest_path = test_data_dir / "manifest.json"
    return json.loads(manifest_path.read_text())


@pytest.fixture
def valid_cases(manifest, test_data_dir) -> list[tuple[dict, Path]]:
    """Returns list of (case_info, file_path) for valid test cases."""
    cases = []
    for case in manifest["test_cases"]:
        if case["expected_valid"]:
            cases.append((case, test_data_dir / case["file"]))
    return cases


@pytest.fixture
def invalid_cases(manifest, test_data_dir) -> list[tuple[dict, Path]]:
    """Returns list of (case_info, file_path) for invalid test cases."""
    cases = []
    for case in manifest["test_cases"]:
        if not case["expected_valid"]:
            cases.append((case, test_data_dir / case["file"]))
    return cases