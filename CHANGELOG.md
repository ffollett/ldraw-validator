# Changelog

All notable changes to the LDraw Validator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive documentation updates
  - Enhanced README with web interface documentation
  - Created CONTRIBUTING.md with development workflow
  - Updated architecture.md with web component diagrams
  - Added CHANGELOG.md for tracking changes

## [0.1.0] - 2026-02-01

### Added
- **Web Interface** - Full-featured Flask application for catalog browsing
  - Part catalog browser with advanced filtering (category, type, extraction status, images, LDraw org)
  - Search functionality by part ID or name
  - Pagination support (50 parts per page)
  - Interactive 3D part viewer using Three.js LDraw loader
  - Statistics dashboard with distribution charts
  - Batch rendering system with real-time progress tracking via Server-Sent Events
  - On-demand part image rendering through web UI
  - Job history tracking for batch operations
  - Thread-safe database connection management

- **Enhanced Catalog System**
  - SQLite database with 12,659 LDraw parts
  - Dual extraction methods (geometric + offLibShadow)
  - Connection point metadata (studs, anti-studs, technic holes)
  - Part categorization and type classification
  - Extraction status tracking (success, partial, failed)
  - Subpart and parent part relationship tracking
  - Rendered image path management

- **Shadow Parser Integration**
  - offLibShadow format parser (`shadow_parser.py`)
  - Explicit connection metadata extraction
  - Support for SNAP_CYL, TUBE, and other connection types
  - Gender and role detection for connections
  - Connection property parsing

- **Grid Alignment Validation**
  - New validation check for LEGO grid alignment
  - Validates X/Z positions (20 LDU stud spacing)
  - Validates Y positions (8 LDU plate height)
  - Warnings for misaligned bricks

- **Batch Rendering Infrastructure**
  - Background thread-based rendering
  - Start/stop/pause batch job controls
  - Real-time progress updates
  - Error logging and recovery
  - Configurable rendering parameters

- **Developer Tools**
  - Debug scripts for connection analysis
  - Debug scripts for parser testing
  - Debug scripts for primitive extraction
  - Verification script for validator functionality

### Changed
- **Catalog Database** (breaking change from pickle to SQLite)
  - Migrated from `catalog.py` with pickle caching to `catalog_db.py` with SQLite
  - Improved query performance with indexed lookups
  - Thread-safe database access patterns
  - Richer metadata storage

- **Renderer Enhancement**
  - Production-quality rendering with configurable dimensions
  - Silent error handling for batch operations
  - Automatic output directory management
  - Better LDView integration

- **Project Structure**
  - Consolidated catalog logic into single database system
  - Reorganized scripts directory
  - Added web/ directory for Flask application
  - Improved separation of concerns

### Fixed
- Renderer now handles missing parts gracefully in batch mode
- Database connection management prevents threading issues
- Improved error handling in catalog extraction

### Performance
- Catalog queries: <10ms for filtered results
- Part rendering: 200-500ms per part via LDView
- Full catalog rebuild: 2-5 minutes
- Validation: ~6ms for 500-piece MOC

## [0.0.1] - 2026-01-29 - "Phase 0 Complete"

Initial release of the LDraw Validator core engine.

### Added
- **Core Validation Engine**
  - LDraw/MPD file parsing (`parser.py`)
  - MPD submodel resolution and transform composition (`loader.py`)
  - Spatial indexing with R-tree (`scene_graph.py`)
  - Connection validation via stud/anti-stud matching (`connections.py`)
  - Grounding analysis with BFS from build plate (`grounding.py`)
  - AABB-based collision detection (`collision.py`)
  - Transform utilities for 3D geometry (`geometry.py`)
  - LDView integration for rendering (`renderer.py`)

- **Catalog System** (original pickle-based)
  - LDraw part parsing and connection point extraction
  - Stud primitive detection (stud.dat, stud2.dat, etc.)
  - Anti-stud inference via heuristics
  - Pickle caching for fast catalog loading
  - Support for 100+ common System bricks

- **Public API**
  - `validate_moc(file_path)` - Main validation function
  - `ValidationResult` dataclass with errors list
  - `ValidationError` dataclass with error types

- **Test Suite**
  - Unit tests for all core components
  - Integration tests with valid/invalid test cases
  - Test data manifest system
  - pytest configuration

- **Documentation**
  - Product Requirements Document (PRD)
  - Architecture overview
  - Strategy document
  - README with quick start guide

- **Scripts**
  - `verify_phase0.py` - Validation verification
  - `build_catalog.py` - Catalog building (pickle version)
  - `validate_moc.py` - CLI validation tool

### Performance Targets Met
- ✅ 500-piece MOC validation in <5s (achieved ~6ms)
- ✅ Zero false negatives on known-valid MOCs
- ✅ Support for standard System bricks

### Known Limitations (Phase 0 Scope)
- No Technic element support (pins, axles, gears)
- No SNOT (Studs Not On Top) connections
- No hinge or ball joint validation
- Limited to <1000 pieces for optimal performance
- No real-time interactive editing

## Version History Summary

| Version | Date       | Key Feature                          |
|---------|------------|--------------------------------------|
| 0.1.0   | 2026-02-01 | Web interface, SQLite catalog        |
| 0.0.1   | 2026-01-29 | Phase 0 core validation engine       |

## Migration Guide

### Upgrading from 0.0.1 to 0.1.0

**Breaking Change: Catalog format changed from pickle to SQLite**

If you have a pickle-based catalog from Phase 0:

```bash
# Rebuild catalog to SQLite format
.venv\Scripts\activate.ps1
python scripts/build_catalog.py
```

**API Changes:**
- `get_part()` now queries SQLite instead of loading pickle
- PartInfo dataclass has additional fields
- Catalog location changed from pickle file to `src/validator/data/catalog.db`

**Benefits:**
- Faster queries with SQL indexing
- Thread-safe for web interface
- Richer metadata and relationship tracking
- Support for 12,000+ parts

## Future Roadmap

### Phase 1 (Planned)
- Synthetic dataset generation
- MOC augmentation tools
- Training data export

### Phase 2 (Planned)
- ML model integration
- Brick detection from images
- Generative MOC creation

### Phase 3+ (Vision)
- Technic connection support
- SNOT validation
- Real-time validation API
- Cloud-hosted service

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development workflow, testing guidelines, and how to submit changes.

## Links

- [Product Requirements Document](docs/prd.md)
- [Architecture Overview](docs/architecture.md)
- [Strategy Document](docs/strategy.md)
- [GitHub Repository](https://github.com/ffollett/ldraw-validator)
- [LDraw.org](https://www.ldraw.org/)

---

**Note on Versioning:**
- Phase 0 = v0.0.x (core engine)
- Phase 1 = v0.1.x (dataset generation + web interface)
- Phase 2 = v0.2.x (ML integration)
- v1.0.0 = Production-ready release
