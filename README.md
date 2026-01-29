# LDraw Validator

**Phase 0: Complete ✅**

A deterministic engine for validating LEGO brick-built models against physical buildability constraints.

## Features

- **LDraw/MPD Parsing**: Load standard LDraw `.ldr` and `.mpd` files with full submodel support
- **Connection Validation**: Verify stud-to-antistud connections with tolerance handling
- **Grounding Analysis**: Detect floating bricks not connected to the build plate
- **Collision Detection**: AABB-based intersection testing with broad/narrow phase optimization
- **Rendering**: Generate images via LDView integration

## Quick Start

```bash
# Install dependencies
pip install -e .

# Validate a MOC
python -c "from validator import validate_moc; print(validate_moc('path/to/model.ldr'))"

# Run verification suite
python scripts/verify_phase0.py
```

## Requirements

- Python 3.10+
- [LDraw Library](https://www.ldraw.org/) installed at `C:\LDraw\ldraw` (or set `LDRAW_PATH`)
- [LDView 4.6+](https://ldview.sourceforge.io/) for rendering (optional)

## Project Structure

```
src/validator/
├── __init__.py      # Main API: validate_moc()
├── parser.py        # LDraw file parsing
├── loader.py        # MPD submodel resolution
├── catalog.py       # Brick connection point extraction
├── scene_graph.py   # Spatial indexing (R-tree)
├── connections.py   # Stud/anti-stud matching
├── grounding.py     # Build plate connectivity
├── collision.py     # Intersection detection
├── geometry.py      # Transform utilities
└── renderer.py      # LDView integration
```

## Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| 500-piece MOC | < 5s | ~6ms avg |
| False negatives | 0 | 0 |

## Documentation

- [Product Requirements Document](docs/prd.md) - Original Phase 0 PRD
- [Architecture Overview](docs/architecture.md) - Technical implementation details

## Status

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

