# Contributing to LDraw Validator

Thank you for your interest in contributing! This document provides guidelines and instructions for developing the LDraw Validator project.

## Table of Contents

- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Structure](#code-structure)
- [Common Tasks](#common-tasks)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [LDraw Library](https://www.ldraw.org/) installed (default location: `C:\LDraw\ldraw`)
- [LDView 4.6+](https://ldview.sourceforge.io/) for rendering (optional but recommended)
- Git

### Initial Setup

```bash
# Clone the repository
git clone <repository-url>
cd lego_validator

# The project uses a pre-configured virtual environment
# Activate it based on your platform:

# Windows PowerShell
.venv\Scripts\activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# Linux/Mac
source .venv/bin/activate

# Install the package in editable mode
pip install -e .

# Verify installation
python -c "from validator import validate_moc; print('✓ Installation successful')"
```

### Environment Configuration

The project uses environment variables for configuration. Create a `.env` file (optional) or set these in your system:

```bash
# LDraw library path (default: C:\LDraw\ldraw on Windows)
LDRAW_PATH=C:\LDraw\ldraw

# LDView executable path (auto-detected if in PATH)
LDVIEW_PATH=C:\Program Files\LDView\LDView.exe
```

## Running Tests

### Test Framework

We use `pytest` for testing. The test suite is located in the `tests/` directory.

### Running Tests

```bash
# Activate virtual environment first!
.venv\Scripts\activate.ps1

# Run all tests with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_catalog.py -v

# Run specific test function
pytest tests/test_catalog.py::TestCatalogUnits::test_stud_primitives_detection -v

# Run with short tracebacks (easier to read)
pytest tests/ -v --tb=short

# Run with coverage report
pytest tests/ --cov=validator --cov-report=html
# Then open htmlcov/index.html
```

### Current Test Status

As of 2026-02-06:
- **Total tests**: 48
- **Passing**: 40 (83%)
- **Failing**: 8 (17%)

#### Known Test Failures

1. **Catalog Tests (2 failures)**
   - `test_get_part_basic`: Expects 8 studs, catalog now extracts 11 (improvement)
   - `test_anti_stud_heuristic`: Anti-stud detection logic needs updating
   
   **Fix**: Update test expectations to match improved catalog extraction

2. **Integration Tests (6 failures)**
   - Various `test_valid_case` failures in tall stacks and complex connections
   - Issue: Grounding detection not recognizing valid connection chains
   
   **Fix**: Debug connection graph building and grounding BFS algorithm

### Test Data

Test data is located in `test_data/` directory:
- `valid/` - Valid MOC files that should pass validation
- `invalid/` - Invalid MOC files that should fail with specific errors
- `edge_cases/` - Unusual but valid configurations
- `manifest.json` - Test case metadata

## Code Structure

### Main Components

```
src/validator/
├── __init__.py           # Public API: validate_moc(), ValidationResult
├── parser.py             # LDraw file format parser
├── loader.py             # MPD submodel resolution
├── catalog_db.py         # Part database (SQLite)
├── scene_graph.py        # Spatial indexing with R-tree
├── connections.py        # Connection point matching
├── grounding.py          # Build plate connectivity (BFS)
├── collision.py          # AABB collision detection
├── geometry.py           # Transformation utilities
├── renderer.py           # LDView subprocess wrapper
├── shadow_parser.py      # offLibShadow format parser
├── checks.py             # Grid alignment validation
└── config.py             # Configuration management
```

### Key Data Structures

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[ValidationError]

@dataclass
class ValidationError:
    error_type: str  # "ungrounded", "collision", "parse_error", "grid_alignment"
    message: str
    brick_indices: list[int]

@dataclass
class Placement:
    part_id: str
    color: int
    position: tuple[float, float, float]
    rotation: tuple[float, ...]  # 3x3 matrix flattened

@dataclass
class PartInfo:
    part_id: str
    part_name: str
    studs: list[list[float]]          # [[x, y, z], ...]
    anti_studs: list[list[float]]
    technic_holes: list[list[float]]
    connection_points: list[dict]     # offLibShadow connections
    # ... more fields
```

## Common Tasks

### Adding a New Validation Check

1. Create validation logic in `src/validator/checks.py` or a new module
2. Call from `validate_moc()` in `src/validator/__init__.py`
3. Add new error type to `ValidationError`
4. Write tests in `tests/test_<module>.py`
5. Add test cases to `test_data/` if needed

Example:

```python
# In checks.py
def validate_new_check(placement: Placement, part_info: PartInfo) -> list[str]:
    """Validate some new constraint."""
    warnings = []
    # Check logic here
    return warnings

# In __init__.py validate_moc()
for i, p in enumerate(placements):
    warnings = validate_new_check(p, get_part(p.part_id))
    for w in warnings:
        errors.append(ValidationError(
            error_type="new_check_type",
            message=f"Part {i}: {w}",
            brick_indices=[i]
        ))
```

### Rebuilding the Catalog

After modifying catalog extraction logic or updating the LDraw library:

```bash
# Activate virtual environment
.venv\Scripts\activate.ps1

# Stop web server if running

# Run catalog builder
python scripts/build_catalog.py

# This takes 2-5 minutes and updates:
# src/validator/data/catalog.db
```

The builder:
- Scans LDraw `parts/` directory
- Extracts connection points (studs, anti-studs, technic holes)
- Parses offLibShadow connection metadata
- Preserves existing rendered images
- Updates SQLite database

### Adding a New Part Attribute

1. Update `PartInfo` dataclass in `catalog_db.py`
2. Modify extraction logic in `build_catalog.py`
3. Update database schema (add migration if needed)
4. Update tests to verify extraction
5. Update web UI to display new attribute

### Visualizing Test Cases

Test cases can be rendered to images for visual inspection:

```bash
# Activate virtual environment
.venv\Scripts\activate.ps1

# Render all test cases
python scripts/visualize_tests.py
```

Output: `test_renders/` with pass/fail badges in filenames:
- `✓_1.1_stacked_bricks.png` - Test passed (matches expectation)
- `✗_2.1_floating_brick.png` - Test failed (doesn't match expectation)

**Future**: Interactive web UI at `/tests` for 3D exploration with validation overlays.


### Working with the Web Interface

```bash
# Start development server
python web/app.py

# Debug mode is enabled by default in __main__ block
# Edit templates in web/templates/
# Edit styles in web/static/style.css
# Flask auto-reloads on file changes
```

#### Web Architecture

- **Backend**: Flask application (`web/app.py`)
- **Database**: SQLite with thread-safe connection pooling
- **Frontend**: HTML templates with vanilla JavaScript
- **3D Viewer**: Three.js with LDraw loader
- **Real-time**: Server-Sent Events for batch rendering progress

#### Adding a New Web Endpoint

```python
# In web/app.py
@app.route('/api/new-endpoint')
def api_new_endpoint():
    conn = get_db()  # Thread-safe connection
    # Query logic
    return jsonify({"data": results})
```

## Code Style

### Python Style

We follow PEP 8 with some modifications:

- **Line length**: 100 characters (not 79)
- **Indentation**: 4 spaces
- **Quotes**: Prefer double quotes for strings
- **Type hints**: Use type hints for function signatures
- **Docstrings**: Use for public functions and classes

### Type Hints

```python
# Good
def get_part(part_id: str) -> PartInfo:
    """Get part info from catalog."""
    ...

# Also good - type hints in variable declarations
studs: list[tuple[float, float, float]] = []

# Use dataclasses for structured data
from dataclasses import dataclass

@dataclass
class MyClass:
    field1: str
    field2: int
```

### Imports

```python
# Standard library
import sys
from pathlib import Path
from dataclasses import dataclass

# Third party
import pytest
from flask import Flask, jsonify

# Local
from validator import validate_moc
from validator.catalog_db import get_part
```

### Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`

## Debugging Tips

### Enable Verbose Logging

```python
# In your test or script
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspecting the Catalog Database

```bash
# Open SQLite database
sqlite3 src/validator/data/catalog.db

# Show schema
.schema parts

# Query parts
SELECT part_id, part_name, studs_json FROM parts LIMIT 10;

# Exit
.quit
```

### Debugging LDView Rendering

```python
# In renderer.py, LDView is called via subprocess
# Check the command being run by adding print statements
# Or run LDView manually:

LDView.exe model.ldr -SaveSnapshot=output.png -SaveWidth=800 -SaveHeight=600
```

### Debugging Connection Detection

```python
# Use debug scripts
python scripts/debug_connection.py path/to/model.ldr

# Or add debug prints in connections.py
from validator.connections import build_connection_graph
from validator.scene_graph import SceneGraph
from validator.loader import Loader

sg = SceneGraph()
loader = Loader(sg)
loader.load("model.ldr")

connections = build_connection_graph(sg)
print(f"Found {len(connections)} connections")
for i, j in connections:
    print(f"  Part {i} <-> Part {j}")
```

## Submitting Changes

### Before Submitting

1. **Run tests**: Ensure existing tests still pass
   ```bash
   pytest tests/ -v
   ```

2. **Add tests**: Write tests for new features

3. **Update docs**: Update README and docstrings as needed

4. **Check style**: Follow code style guidelines

5. **Test manually**: Run the validation on sample MOCs

### Commit Messages

Use clear, descriptive commit messages:

```
Good:
- "Add grid alignment validation check"
- "Fix grounding detection for tall stacks"
- "Update catalog extraction to detect tube studs"

Less good:
- "Fix bug"
- "Update code"
- "Changes"
```

### Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit
3. Push to your fork: `git push origin feature/my-feature`
4. Open a pull request with:
   - Clear description of changes
   - Reference to related issues
   - Test results
   - Screenshots (for UI changes)

## Getting Help

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check `docs/` directory for detailed architecture

## Project Roadmap

See [docs/prd.md](docs/prd.md) and [docs/strategy.md](docs/strategy.md) for:
- Phase 0 completion status
- Phase 1 plans (synthetic dataset generation)
- Phase 2 plans (ML integration)
- Long-term vision

---

Thank you for contributing to LDraw Validator! 🧱
