# PRD: LDraw Validator (Phase 0)

## Overview

This document describes the first technical milestone for a LEGO MOC verification system: a deterministic engine that can load brick-built models, validate their physical buildability, and render them. This engine serves as the foundation for all downstream ML work—without reliable verification, we cannot evaluate generative model quality or provide meaningful feedback to human annotators.

---

## Problem Statement

There is currently no open, programmatic way to answer the question "is this collection of LEGO bricks physically buildable?" Existing tools like BrickLink Studio or LDraw viewers will render whatever you give them, including physically impossible configurations. We need a verification layer that enforces real-world LEGO constraints: pieces must connect at valid connection points, pieces cannot intersect, and all connections must be structurally sound.

This engine will eventually sit in an automated pipeline evaluating AI-generated MOC candidates, but it must first work reliably on known-good MOCs created by humans.

---

## Success Criteria

The phase is complete when we can demonstrate the following workflow: load any LDraw-format MOC file containing basic System bricks (plates, bricks, tiles), validate all piece placements against physical constraints, report specific errors for invalid configurations, and render valid configurations to an image file.

Quantitatively, we target processing of MOCs up to 500 pieces in under 5 seconds on commodity hardware, correct validation of at least 50 community MOCs from the LDraw OMR (Official Model Repository), and zero false negatives on known-valid models (we should never reject a buildable MOC).

---

## Scope

### In Scope

The engine will support basic System bricks: standard bricks (1xN, 2xN), plates, tiles, and slopes in common dimensions. We will handle stud-to-antistud connections, which represent the fundamental LEGO connection mechanism, and plate stacking at correct height intervals (plate height is one-third brick height). The engine will detect collision between pieces occupying the same space and identify floating pieces with no valid connections. We will parse standard LDraw .ldr and .mpd file formats and produce PNG renders of validated models.

### Out of Scope for Phase 0

Technic elements (pins, axles, gears, beams) introduce rotational connections and require substantially different constraint logic. Specialty elements like hinges, ball joints, minifigure parts, and decorative elements add complexity without proving core feasibility. SNOT (studs not on top) connections via specialized bricks will be deferred. Performance optimization for MOCs beyond 1000 pieces is not required for the POC. We will not build a real-time interactive editor—this is a batch validation tool.

---

## Technical Architecture

### Component 1: Brick Catalog

The brick catalog is a database of known LEGO elements with their geometric and connection properties.

Each brick entry contains a unique part identifier matching LDraw numbering conventions, bounding box dimensions in LDraw units (LDU), and a list of connection points. Each connection point specifies its position relative to the brick origin, connection type (stud, anti-stud, or plate-stack surface), and orientation vector.

We will bootstrap this catalog by parsing LDraw part files. LDraw parts are defined as line-based geometry primitives, and stud positions can be inferred from references to standard stud subparts (stud.dat, stud2.dat, etc.). For the POC, we will manually verify connection point extraction for the 50 most common brick types and automate extraction for the long tail.

The catalog should be serialized to a fast-loading format (SQLite or flat JSON) so we don't re-parse LDraw files on every engine invocation.

### Component 2: Scene Graph

A scene graph represents a MOC as a collection of placed bricks.

Each placed brick references a catalog entry, a position vector (x, y, z) in LDU, and a rotation matrix. LDraw uses a 4x4 transformation matrix; we'll decompose this into position and rotation for easier manipulation.

The scene graph must support spatial queries: given a point or volume, return all bricks that occupy or intersect that region. We will use a spatial index structure (R-tree or octree) to make these queries efficient. The expected access patterns are point queries to find what connects at a given stud position and box queries to detect collisions.

Loading an LDraw file populates the scene graph. We will use an existing LDraw parser as a starting point rather than writing one from scratch—several Python implementations exist on GitHub with permissive licenses.

### Component 3: Connection Validator

The connection validator checks whether placed bricks form valid connections.

For each placed brick, we transform its connection points from local to world coordinates. We then query the spatial index for nearby connection points from other bricks. Two connection points form a valid connection if they are complementary types (stud connects to anti-stud), their positions match within a small tolerance (1 LDU or less), and their orientation vectors are compatible (stud pointing up connects to anti-stud pointing down).

A brick is "grounded" if it has at least one valid connection to another grounded brick, or if it sits on the build plate (y=0 with anti-studs facing down). We perform a graph traversal starting from build-plate bricks to identify all grounded bricks. Any ungrounded bricks are flagged as errors.

We must handle the case where a brick has multiple connection points—it only needs one valid connection to be grounded, though we may want to warn about "weak" connections in future phases.

### Component 4: Collision Detector

The collision detector identifies illegal overlaps between bricks.

For each pair of potentially overlapping bricks (identified via spatial index query), we perform detailed geometric intersection testing. LDraw geometry is complex (studs, internal tubes, etc.), but for the POC we can approximate each brick as a simple box minus the stud cavities on the bottom.

Two bricks collide if their solid volumes intersect. Studs fitting into anti-stud cavities is the intended behavior and should not register as collision. We'll need careful handling of the tolerance here—real LEGO has clutch power precisely because there's slight interference fit, but that's at a sub-millimeter scale we can treat as zero for validation purposes.

Detected collisions are flagged as errors with the specific brick pair identified.

### Component 5: Renderer

The renderer produces images of validated MOCs for visual inspection and downstream ML training.

For the POC, we will shell out to an existing renderer rather than building our own. Options include Blender with an LDraw import add-on, which produces photorealistic output but has slower startup time. LDView is a dedicated LDraw viewer with command-line rendering support that offers faster execution and good-enough quality. POV-Ray with LDraw-to-POV conversion is another option that produces high quality output but involves a more complex pipeline.

We will wrap the chosen renderer in a Python interface that accepts a validated scene graph and camera parameters and returns an image file path. Camera parameters should include orbital position (azimuth, elevation, distance) and optional focal point. We'll want consistent, reproducible renders for training data generation.

---

## Data Flows

The primary flow begins when an LDraw file is read from disk and passed to the parser. The parser converts it to a scene graph, populating brick placements and building the spatial index. The scene graph then passes to the connection validator, which returns a validation report listing any connection errors. If validation passes, the scene graph proceeds to collision detection, which returns a collision report. If no collisions are found, the scene graph proceeds to the renderer along with camera parameters, producing an output image. All reports combine into a final validation result returned to the caller.

The validation result should be structured data (JSON or similar) containing overall pass/fail status, a list of error objects each specifying error type, affected brick identifiers, and human-readable description, and metadata about the MOC including piece count, dimensions, and validation time.

---

## Implementation Plan

### Week 1: Brick Catalog Foundation

The first task is evaluating and selecting an LDraw parser library. We will test ldraw-parser (Python) and ldrawpy against a sample of LDraw files to assess completeness and correctness. Selection criteria include correct handling of MPD files with submodels, proper transformation matrix parsing, and reasonable performance on files over 1000 lines.

The second task is designing the catalog schema. We will define data structures for brick entries and connection points and decide on serialization format. The third task is implementing stud detection by writing code that analyzes parsed LDraw geometry to find stud positions. We will start with explicit stud subpart references (stud.dat, stud2.dat, stud3.dat, stud4.dat) and handle inline stud geometry as a fallback. The final task of the week is manual verification, where we validate extracted connection points for 20 common bricks against physical LEGO pieces or reference documentation.

The deliverable for week 1 is a catalog covering 100+ basic System bricks with verified connection points.

### Week 2: Scene Graph and Spatial Indexing

The first task is implementing the scene graph data structure with brick placement representation and transformation handling. We will ensure correct conversion between LDraw coordinate system and our internal representation. The second task is integrating a spatial index using rtree or scipy.spatial for R-tree implementation. We will define the interface for point and box queries and test query performance with synthetic scenes of varying sizes.

The third task is building the LDraw loader that connects the parser to scene graph construction. We will handle MPD submodel references and file path resolution and add error handling for missing parts and malformed files. The final task is validation, testing scene graph construction on 10 OMR models and verifying brick counts and positions match expected values.

The deliverable for week 2 is a loader that correctly imports OMR models into queryable scene graphs.

### Week 3: Connection Validation

The first task is implementing connection point transformation, converting local connection points to world coordinates based on brick placement and handling rotation matrices correctly including common 90-degree and 45-degree rotations.

The second task is implementing connection matching. We will write the core logic for finding valid stud/anti-stud pairs, define tolerance values based on LDraw standard dimensions, and handle edge cases including bricks with many connection points and connection points at model boundaries.

The third task is implementing grounding analysis using graph traversal from build-plate bricks and identifying floating subassemblies that connect to each other but not to ground.

The fourth task is building the error reporting system with a structured error format for connection failures and adding contextual information including which connection points failed to match and what nearby candidates existed.

The deliverable for week 3 is a validator that correctly identifies connection errors in intentionally malformed test MOCs.

### Week 4: Collision Detection and Renderer Integration

The first task is implementing collision detection. We will start with bounding box intersection as a broad phase and implement narrow phase testing accounting for stud cavities. We will test on cases including legally stacked bricks, illegally intersecting bricks, and near-miss configurations.

The second task is integrating the renderer. We will select the renderer based on quality/speed tradeoffs evaluated during week 1 parser work. We will write a wrapper providing a simple Python API and implement camera parameter handling for consistent viewpoints.

The third task is building the end-to-end pipeline, connecting all components into a single validation function and implementing the structured output format. The fourth task is validation testing against 50 OMR models. All should pass validation and render successfully. We will test performance and verify the target of under 5 seconds for 500 pieces is met.

The deliverable for week 4 is a complete phase 0 engine demonstrable on community MOCs.

---

## Test Strategy

### Unit Tests

The brick catalog tests verify that connection point extraction produces expected results for known bricks. The scene graph tests verify that spatial queries return correct results for hand-constructed scenes. The connection validator tests verify correct behavior on minimal cases including two bricks connected, two bricks not connected, floating brick, and grounded brick.

### Integration Tests

Positive cases use OMR models that are known-valid and should pass validation without errors. Negative cases use hand-crafted invalid MOCs that should produce specific expected errors. Round-trip cases involve loading a model, validating it, and verifying that re-serializing to LDraw produces equivalent output.

### Performance Tests

Scaling tests measure validation time versus piece count and verify linear or near-linear scaling. Memory tests measure memory usage versus piece count and ensure we don't exceed reasonable bounds for 1000-piece models.

---

## Risks and Mitigations

### Risk: LDraw Connection Point Extraction Proves Unreliable

LDraw parts vary in how they represent studs—some use subpart references, others inline geometry. If automated extraction fails too often, we may need extensive manual annotation.

Mitigation: Start with the most common 50 bricks and manually verify all of them. If more than 20% require manual correction, scope down the POC to only those 50 bricks and defer broader coverage.

### Risk: Collision Detection Performance

Naive pairwise collision checking is O(n²). Spatial indexing should reduce this, but complex MOCs might still be slow.

Mitigation: Implement broad-phase culling aggressively. If performance remains problematic, consider approximate methods (voxelization) for the POC with exact methods deferred.

### Risk: LDraw Coordinate System Complexity

LDraw uses a Y-up coordinate system with unintuitive scale (20 LDU = 1 stud width). Transformation bugs could cause subtle validation errors.

Mitigation: Build a comprehensive test suite of known configurations before implementing validation logic. Include visual debugging tools that render connection points in 3D.

### Risk: Renderer Integration Friction

External renderers may have installation complexity, version incompatibility, or unreliable command-line interfaces.

Mitigation: Evaluate renderer options in week 1 in parallel with catalog work. Have a fallback plan using simple matplotlib-based wireframe rendering if proper rendering proves too difficult.

---

## Open Questions

How should we handle color? LDraw includes color information, and some bricks only exist in certain colors. For phase 0, we likely ignore color for validation but preserve it for rendering. Should we validate color availability later?

How do we handle unofficial parts? The LDraw library includes unofficial parts that may have inconsistent quality. Should the POC reject MOCs using unofficial parts, or attempt best-effort validation?

What is our ground truth for connection validity? Some LEGO connections are technically possible but not recommended (weak clutch, stress on parts). Do we validate only geometry, or also structural integrity? For phase 0, geometry-only seems appropriate.

Should we support multiple disconnected subassemblies? Some MOCs intentionally include separate pieces (a minifigure next to a vehicle). Do we require everything to connect, or allow intentional floating pieces with explicit annotation?

---

## Future Work

Phase 1 will use this engine to evaluate brick detection models on synthetic renders. Phase 2 will use validation scores as training signal for generative models. Later phases will extend the engine to support Technic, SNOT, and specialty connections.

The phase 0 engine should be designed with these extensions in mind, but implementing them is explicitly out of scope.