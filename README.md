# LDraw Validator

**Phase 0: Complete ✅**

A deterministic engine for validating LEGO brick-built models against physical buildability constraints.

## Features

### Core Validation Engine
- **LDraw/MPD Parsing**: Load standard LDraw `.ldr` and `.mpd` files with full submodel support
- **Connection Validation**: Verify stud-to-antistud connections with tolerance handling
- **Grounding Analysis**: Detect floating bricks not connected to the build plate
- **Collision Detection**: AABB-based intersection testing with broad/narrow phase optimization
- **Rendering**: Generate images via LDView integration

### Web Interface
- **Part Catalog Browser**: Explore 12,000+ LDraw parts with advanced filtering
- **Interactive 3D Viewer**: Visualize parts directly in the browser using Three.js
- **Statistics Dashboard**: View distribution charts and catalog analytics
- **Batch Rendering**: Render part images in bulk with real-time progress tracking

## Quick Start

### Validate a MOC

```bash
# Activate virtual environment
.venv\Scripts\activate.ps1  # Windows PowerShell

# Validate a MOC file
python -c "from validator import validate_moc; from pathlib import Path; print(validate_moc(Path('path/to/model.ldr')))"
```

### Start the Web Interface

```bash
# Activate virtual environment
.venv\Scripts\activate.ps1  # Windows PowerShell

# Start the web server
python web/app.py
```

Then open <http://localhost:5000> in your browser.

## Requirements

- Python 3.10+
- [LDraw Library](https://www.ldraw.org/) installed at `C:\LDraw\ldraw` (or set `LDRAW_PATH`)
- [LDView 4.6+](https://ldview.sourceforge.io/) for rendering (optional)

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd lego_validator

# Activate the virtual environment
.venv\Scripts\activate.ps1  # Windows PowerShell
# or: .venv\Scripts\activate  # Windows CMD
# or: source .venv/bin/activate  # Linux/Mac

# Install in editable mode
pip install -e .
```

## Project Structure

```
src/validator/
├── __init__.py      # Main API: validate_moc()
├── parser.py        # LDraw file parsing
├── loader.py        # MPD submodel resolution
├── catalog_db.py    # Part database and connection extraction
├── scene_graph.py   # Spatial indexing (R-tree)
├── connections.py   # Stud/anti-stud matching
├── grounding.py     # Build plate connectivity
├── collision.py     # Intersection detection
├── geometry.py      # Transform utilities
├── renderer.py      # LDView integration
├── shadow_parser.py # offLibShadow integration
└── checks.py        # Grid alignment validation

web/
├── app.py           # Flask web application
├── templates/       # HTML templates
└── static/          # CSS, JavaScript, images

tests/               # Test suite (pytest)
scripts/             # Utility scripts
docs/                # Documentation
```

## Web Interface

The web interface provides a comprehensive tool for exploring the LDraw part catalog.

### Features

- **Catalog Browser**: Browse and filter 12,659 parts by:
  - Category (Brick, Plate, Tile, Slope, etc.)
  - Type (standard types + "Other")
  - Extraction status (success, partial, failed)
  - Presence of rendered images
  - LDraw organization type (Part, Shortcut, Primitive)
  - Search by part ID or name

- **3D Viewer**: Interactive visualization using Three.js LDraw loader
  - Rotate, zoom, pan controls
  - Real-time part rendering

- **Statistics Dashboard**: Catalog analytics including:
  - Distribution charts (pie charts for categorical data)
  - Histograms for numeric data (heights, stud counts)
  - Connection point type breakdown
  - Extraction status overview

- **Batch Rendering**: 
  - Render multiple parts at once with customizable filters
  - Real-time progress updates via Server-Sent Events
  - Start/stop job control
  - Job history tracking

- **On-Demand Rendering**: Generate individual part images through the UI

### Starting the Server

```bash
# Activate virtual environment
.venv\Scripts\activate.ps1

# Start Flask application
python web/app.py

# Server will start on http://localhost:5000
```

## API Usage

```python
from validator import validate_moc, ValidationResult
from pathlib import Path

# Validate a MOC file
result: ValidationResult = validate_moc(Path("model.ldr"))

if result.is_valid:
    print("✓ MOC is valid!")
else:
    print("✗ MOC has errors:")
    for error in result.errors:
        print(f"  - {error.error_type}: {error.message}")
        if error.brick_indices:
            print(f"    Affected bricks: {error.brick_indices}")
```

### Error Types

- `parse_error`: Failed to parse LDraw file
- `collision`: Two or more bricks intersect illegally
- `ungrounded`: Brick is not connected to the build plate
- `grid_alignment`: Brick position doesn't align to LEGO grid

## Development

### Running Tests

```bash
# Activate virtual environment
.venv\Scripts\activate.ps1

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_catalog.py -v

# Run with coverage
pytest tests/ --cov=validator --cov-report=html
```

**Current Test Status**: 40 passed, 8 failed (83% pass rate)

Known issues:
- 2 catalog tests expect outdated stud counts (catalog has improved)
- 6 integration tests have grounding detection edge cases being investigated

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development workflow.

### Rebuilding the Catalog

If you update the LDraw library or modify extraction logic:

```bash
# Activate virtual environment
.venv\Scripts\activate.ps1

# Stop web server if running

# Rebuild the catalog database
python scripts/build_catalog.py
```

This process:
- Updates existing parts with new data
- Adds newly discovered parts
- **Preserves** existing rendered images
- Takes 2-5 minutes on average
- Creates/updates `src/validator/data/catalog.db` (SQLite database)

### Batch Rendering Parts

```bash
# Render parts via command line
python scripts/download_part_images.py

# Or use the web interface for more control
python web/app.py
# Then navigate to http://localhost:5000/batch
```

## Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| 500-piece MOC | < 5s | ~6ms avg |
| False negatives | 0 | 0 |
| Catalog parts | 10,000+ | 12,659 |

## Documentation

- [Product Requirements Document](docs/prd.md) - Original Phase 0 PRD
- [Architecture Overview](docs/architecture.md) - Technical implementation details
- [Strategy Document](docs/strategy.md) - Long-term planning (internal)
- [Testing Strategy](docs/testing_strategy.md) - Coverage matrix and validation plans
- [Contributing Guide](CONTRIBUTING.md) - Development workflow

## Project Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Core validation engine | ✅ Complete |
| 1 | Synthetic dataset generation | 🔜 Next |
| 2 | ML training integration | 📋 Planned |

## License

MIT

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by the LEGO Group. LEGO® is a trademark of the LEGO Group of companies which does not sponsor, authorize, or endorse this project.

This tool works with LDraw™ format files, an open standard maintained by the LDraw community.
