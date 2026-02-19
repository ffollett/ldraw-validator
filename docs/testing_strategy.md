# Testing Strategy & Coverage

This document codifies the testing strategy for the LDraw Validator, enumerating the types of parts, validation scenarios, and current test coverage. It serves as a roadmap for expanding the test suite to cover the entire problem space of LEGO validation.

## 1. Problem Space: Validating Physical Feasibility

The core mission is to validate that a digital LEGO model (LDraw/MPD) can be physically built. This requires checking:
1.  **Geometric Validity**: Parts must not intersect (Collision).
2.  **Structural Integrity**: Parts must be connected to the build plate (Grounding).
3.  **Connection Logic**: Connections must be legal (Studs fit in Tubes, Pins fit in Holes).
4.  **Grid Alignment**: Parts must align to the LEGO system grid.

## 2. Part Taxonomy (Aligned with Catalog Database)

The validator's taxonomy is derived directly from the `catalog.db`, specifically using the `type` field (extracted from the first word of the part's description).

| DB Type | Description | Volume (Parts) | Validation Complexity | Current Support |
| :--- | :--- | :--- | :--- | :--- |
| **Brick / Plate / Tile** | Standard cuboid elements | ~2,600 | Low (AABB sufficient) | ✅ Full |
| **Slope / Arch** | Sloped and curved geometry | ~450+ | Medium (Requires Convex Hull) | ⚠️ Partial (Box approx) |
| **Technic** | Holes, Beams, Pins, Axles | ~720+ | Medium-High (Precise fit) | ⚠️ Partial (Holes only) |
| **Minifig / Figure / Animal**| Organic/Complex shapes | ~2,800+ | High (Complex mesh) | ❌ Bounds only |
| **Baseplate** | Build plate surfaces | ~180 | Low | ✅ Ground anchor |
| **Electric** | Motors, sensors, cables | ~600+ | High (Connection logic) | ❌ Bounds only |
| **Sticker / Pattern** | Decorative elements | ~2,000 | N/A | ❌ Ignored |

*Counts based on catalog as of 2026-02-08. Total catalog parts: 12,659.*

### 2.1 Primitives (The "Atoms" of Validation)
Validation relies on identifying specific primitives within parts:
-   **Studs**: `stud.dat`, `stud*.dat` (Male connection)
-   **Tubes/Antistuds**: Inferred from geometry or `!CONNECTOR` metadata (Female connection)
-   **Technic Holes**: `peghole.dat`, `axlehole.dat` (Female connection)
-   **Pins/Axles**: `con*.dat` (Male connection)

## 3. Test Types & Scenarios

We employ a multi-layered testing approach, ranging from unit tests to full model internal consistency checks.

### 3.1 Validation Scenarios (Integration Tests)

These tests run the full validation engine against specific `.ldr` files designed to exercise edge cases.

#### A. Connection Tests
*Verifies that the engine correctly identifies connected parts.*
*   **Standard Stacking**: 1xN Brick on 1xN Brick.
*   **Offset/Bridging**: Brick connecting two underlying bricks.
*   **Rotated Connection**: 90° turn using 1x1 brick or jumper plate.
*   **SNOT Connection**: Headlight brick connecting sideways.
*   **Technic Pin**: Pin connecting two beams (Future).

#### B. Grounding Tests
*Verifies the BFS/DFS graph traversal for grounding.*
*   **Simple Tower**: Stack of bricks grounded at base.
*   **Bridge**: Structure grounded at two points.
*   **Cantilever**: Overhanging structure (must be connected).
*   **Floating Parts**: Validating detection of disconnected clusters.
*   **Submodels**: verifying grounding propagates through MPD submodels.

#### C. Collision Tests
*Verifies geometric intersection detection.*
*   **Standard Overlap**: Two bricks occupying same space.
*   **Partial Overlap**: Bricks intersecting by < 100%.
*   **Touching**: Adjacent bricks (Should NOT collide).
*   **Stud-in-Hole**: Studs inserting into tubes (Should NOT collide). *Currently handled by AABB shrink heuristic.*

#### D. Grid Alignment
*Verifies parts are on effective grid positions.*
*   **Standard Grid**: Position % 20 LDU == 0.
*   **Half-Stud Offset**: Jumper plates (Position % 10 LDU == 0).
*   **Micro-Adjustments**: SNOT offsets.

### 3.2 Unit Tests
*   **Parser**: Correctly parses LDraw lines, steps, and matrices.
*   **Geometry**: Matrix multiplication, AABB calculation, Transform logic.
*   **Spatial Index**: R-Tree insertion and query accuracy.

## 4. Current Coverage Matrix

This matrix tracks our coverage of the problem space.

| Test Type | Standard Bricks | Slopes/Curves | Technic | SNOT/Hinges | Large MOCs |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Parsing** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Collision** | ✅ (AABB) | ⚠️ (Box approx) | ⚠️ (Box approx) | ⚠️ (Box approx) | ✅ |
| **Connections** | ✅ (Studs) | ✅ (Studs) | ⚠️ (Holes only) | ✅ (Studs) | ❓ |
| **Grounding** | ✅ | ✅ | ⚠️ (Complex graph)| ✅ | ❓ |
| **Rendering** | ✅ | ✅ | ✅ | ✅ | ✅ |

*Legend: ✅ Covered/Supported, ⚠️ Partial/Approximated, ❌ Not Supported, ❓ Unknown/Untested*

## 5. Expansion Plan & Roadmap

To achieve "Model Release" quality, we must expand test coverage in these dimensions:

1.  **Refined Collision (Phase 1)**:
    -   Implement **Oriented Bounding Boxes (OBB)** or **Convex Hulls** for slopes to prevent false positives.
    -   Add specific "Slope vs Slope" test cases.

2.  **Technic Validation (Phase 2)**:
    -   Add explicit test cases for `Axle -> Axlehole` and `Pin -> Peghole`.
    -   Implement friction/rotation checks (optional).

3.  **Complex Geometry (Phase 3)**:
    -   Validate SNOT connections (e.g., Erling bricks, Headlight bricks).
    -   Validate Hinges/Turntables (Dynamic connectivity).

4.  **Scale Testing (Phase 4)**:
    -   Import and validate validation on official sets (e.g., 500+ pieces).
    -   Measure performance regression.

## 6. Test Data Enumeration

We maintain a manifest of test data in `test_data/manifest.json`.

*   `valid/1.x`: Basic valid structures.
*   `invalid/2.x`: Specific failures (Floating, Collision).
*   `edge_cases/3.x`: Complex valid scenarios (offsets, tiling).
*   `edge_cases/4.x`: MPD/Submodel scenarios.

**Missing Test Data (To Be Added):**
*   [ ] `slopes/`: Slope stacking, Slope inverts.
*   [ ] `technic/`: Beam connection, Axle alignment.
*   [ ] `snot/`: Headlight brick usage, bracket usage.
*   [ ] `hinges/`: Hinge alignment.
