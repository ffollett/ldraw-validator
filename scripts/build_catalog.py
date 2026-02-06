#!/usr/bin/env python
"""
Parallel batch extraction of part data from LDraw library.
Populates SQLite catalog with studs, bounds, and classification.

Usage:
    python scripts/build_catalog.py
"""

import sys
import os
from pathlib import Path
from multiprocessing import Pool, cpu_count
from typing import Tuple, List, Optional, Any
import re
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validator.catalog_db import init_db, save_part, PartInfo, DB_PATH
from validator.config import get_parts_dir, get_p_dir
from validator.parser import parse_line
from validator.geometry import transform_point_by_matrix
from validator.shadow_parser import ShadowParser

# Primitives that indicate connection points
STUD_PRIMITIVES = {
    "stud.dat", "stud2.dat", "stud3.dat", "stud4.dat", "stud6.dat",
    "stud10.dat", "stud12.dat", "stud15.dat", "studp01.dat", "studel.dat"
}
TECHNIC_HOLE_PRIMITIVES = {
    "peghole.dat", "peghole2.dat", "axlehole.dat", "axlehol2.dat",
    "axlehol3.dat", "axlehol4.dat", "axlehol5.dat", "axlehol6.dat",
    "axlehol7.dat", "axlehol8.dat", "axlehol9.dat",
    "connect.dat", "connect2.dat", "connect3.dat"
}




def get_ldraw_category(part_path: Path) -> Optional[str]:
    """Extract raw !CATEGORY metadata from LDraw file."""
    try:
        with open(part_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if '!CATEGORY' in line:
                    match = re.search(r'!CATEGORY\s+(.+)', line)
                    if match:
                        return match.group(1).strip()
                elif line and not line.startswith('0'):
                    # End of header section
                    break
    except Exception:
        pass
    return None


def get_ldraw_org(part_path: Path) -> Optional[str]:
    """Extract !LDRAW_ORG metadata from LDraw file."""
    try:
        with open(part_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if '!LDRAW_ORG' in line:
                    match = re.search(r'!LDRAW_ORG\s+(.+)', line)
                    if match:
                        val = match.group(1).strip()
                        return val.split()[0] if val else None
                elif line and not line.startswith('0'):
                    # End of header section
                    break
    except Exception:
        pass
    return None


def get_part_name(part_path: Path) -> str:
    """Extract part name (description) from LDraw file.
    
    The first line of an LDraw file is the description/name.
    Example: "0 Brick  2 x  4"
    """
    try:
        with open(part_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
            if first_line.startswith('0 '):
                name = first_line[2:].strip()
                # Clean up common prefixes
                if name.startswith('~'):
                    # Remove tilde prefix (used for moved/internal parts)
                    name = name[1:].strip()
                return name
    except Exception:
        pass
    return part_path.stem  # Fall back to part ID


def get_part_type(part_name: str) -> Optional[str]:
    """Extract first word from part name as type."""
    if not part_name:
        return None
    # Remove leading special characters like =, ~, _
    clean_name = part_name.lstrip('=~_ ')
    words = clean_name.split()
    return words[0] if words else None


def get_recursive_primitives(part_path: Path, matrix: Tuple[float, ...] = None, depth: int = 0, visited: set = None) -> List[Tuple[str, Tuple[float, float, float], Tuple[float, ...]]]:
    """
    Recursively find all primitives (studs, holes) in an LDraw file.
    Returns list of (filename, position, rotation_matrix).
    """
    if visited is None:
        visited = set()
    
    # Avoid infinite recursion
    if depth > 5 or str(part_path) in visited:
        return []
        
    visited.add(str(part_path))
    
    if matrix is None:
        # Identity matrix (3x3 rotation)
        matrix = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        
    primitives = []
    
    try:
        # Resolve path if checking relative include (though we usually pass absolute)
        if not part_path.exists():
            # Try finding in library search paths
            from validator.config import get_parts_dir, get_p_dir
            search_paths = [get_parts_dir(), get_p_dir()]
            found = False
            for sp in search_paths:
                 candidate = sp / part_path.name
                 if candidate.exists():
                     part_path = candidate
                     found = True
                     break
            if not found:
                return []

        with open(part_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.split()
                if not parts or parts[0] != '1':
                    continue
                    
                cmd = parse_line(line)
                if not cmd:
                    continue
                    
                sub_file = cmd.file.lower().replace('\\', '/')
                
                # Transform position
                # New pos = current_matrix * local_pos
                # But wait, local_pos is actually the offset in the *current file's frame*
                # We need to accumulate the transformation.
                # If we are in World Frame W, and included Part P is at M_p relative to W.
                # Inside P, Subpart S is at M_s relative to P.
                # S relative to W is M_p * M_s.
                
                # Construct matrix for this line/command
                # cmd.matrix is 3x3 rotation. cmd.pos is translation.
                # Combined matrix is 4x4 usually, but we keep them separate.
                
                # New Rotation = Current_Rotation * Line_Rotation
                # New Translation = Current_Translation + Current_Rotation * Line_Translation
                
                # Unpack current matrix (row-major 3x3)
                r11, r12, r13, r21, r22, r23, r31, r32, r33 = matrix
                
                # Line translation (tx, ty, tz)
                ltx, lty, ltz = cmd.pos
                
                # Transformed translation (relative to root)
                # Wait, this 'matrix' arg is the ACCUMULATED rotation so far.
                # This 'part_path' file is placed at 'matrix' relative to root.
                # But `extract_part_data` calls this with Identity?
                # No, recursion should pass the accumulated matrix.
                
                # Need to pass position too? Yes.
                # So API should accept (pos, matrix).
                # Refactoring to handle pos later. For now, assume pos is handled alongside.
                pass
                
    except Exception:
        pass
        
    return primitives

# Correct implementation of recursive search with matrix mult
def find_primitives_recursive(part_path: Path, current_pos: Tuple[float, float, float], current_rot: Tuple[float, ...], visited: set) -> List[Tuple[str, Tuple[float, float, float], Tuple[float, ...]]]:
    if str(part_path) in visited:
        return []
    visited.add(str(part_path))
    
    results = []
    
    try:
        # Resolve file path
        actual_path = part_path
        if not actual_path.exists():
            # Try parts/ and p/
            from validator.config import get_parts_dir, get_p_dir
            # Heuristic: try parts/filename, p/filename, parts/s/filename, p/s/filename
            # But usually we just check if it exists in parts list.
            # Using simple check:
            candidates = [
                 get_parts_dir() / part_path.name,
                 get_p_dir() / part_path.name,
                 get_parts_dir() / "s" / part_path.name,
                 get_p_dir() / "48" / part_path.name # low res?
            ]
            for c in candidates:
                # print(f"Checking {c} ... {c.exists()}")
                if c.exists():
                    actual_path = c
                    break
            else:
                # print(f"Could not resolve {part_path}")
                return [] # file not found
    
        # print(f"Scanning {actual_path}")
        with open(actual_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.startswith('1 '):
                    continue
                cmd = parse_line(line)
                if not cmd:
                    continue
                    
                sub_file = cmd.file.lower().replace('\\', '/')
                # print(f"  Found subfile: {sub_file}")
                
                # Calculate new transform
                # Pos = Current_Pos + Current_Rot * Cmd_Pos
                cpx, cpy, cpz = current_pos
                cr11, cr12, cr13, cr21, cr22, cr23, cr31, cr32, cr33 = current_rot
                lpx, lpy, lpz = cmd.pos
                
                # Rotated local pos
                rx = cr11*lpx + cr12*lpy + cr13*lpz
                ry = cr21*lpx + cr22*lpy + cr23*lpz
                rz = cr31*lpx + cr32*lpy + cr33*lpz
                
                new_pos = (cpx + rx, cpy + ry, cpz + rz)
                
                # New Rot = Current_Rot * Cmd_Rot
                lr11, lr12, lr13, lr21, lr22, lr23, lr31, lr32, lr33 = cmd.rot
                
                new_rot = (
                    cr11*lr11 + cr12*lr21 + cr13*lr31,
                    cr11*lr12 + cr12*lr22 + cr13*lr32,
                    cr11*lr13 + cr12*lr23 + cr13*lr33,
                    
                    cr21*lr11 + cr22*lr21 + cr23*lr31,
                    cr21*lr12 + cr22*lr22 + cr23*lr32,
                    cr21*lr13 + cr22*lr23 + cr23*lr33,
                    
                    cr31*lr11 + cr32*lr21 + cr33*lr31,
                    cr31*lr12 + cr32*lr22 + cr33*lr32,
                    cr31*lr13 + cr32*lr23 + cr33*lr33
                )
                
                # Check primitive
                if sub_file in STUD_PRIMITIVES or sub_file in TECHNIC_HOLE_PRIMITIVES:
                    results.append((sub_file, new_pos, new_rot))
                else:
                    # Recurse
                    # We only recurse if it looks like a subpart (s/...) or just any part?
                    # Recurse all, but limit depth is handled by visited check (partially)
                    # Ideally we check logic: Is it a primitive we don't care about?
                    # Most primitives not in our set we can skip? No, 'box.dat' isn't interesting but might contain studs? No.
                    # Usually only 's/...' subfiles contain useful geometry features.
                    # Primitives in 'p/' usually are terminals.
                    # We can heuristic: if starts with 's\' or 's/', recurse.
                    if sub_file.startswith('s/') or sub_file.startswith('s\\') or '48/' in sub_file or 'stug' in sub_file:
                         results.extend(find_primitives_recursive(Path(sub_file), new_pos, new_rot, visited.copy()))
                         
    except Exception:
        pass
        
    return results

def calculate_bounds_recursive(part_path: Path, current_pos: Tuple[float, float, float], current_rot: Tuple[float, ...], visited: set) -> Optional[Tuple[float, float, float, float, float, float]]:
    # Returns (min_x, max_x, min_y, max_y, min_z, max_z) or None
    if str(part_path) in visited:
        return None
    visited.add(str(part_path))
    
    inf = float('inf')
    min_x, max_x = inf, -inf
    min_y, max_y = inf, -inf
    min_z, max_z = inf, -inf
    found_any = False
    
    def update(x, y, z):
        nonlocal min_x, max_x, min_y, max_y, min_z, max_z, found_any
        min_x, max_x = min(min_x, x), max(max_x, x)
        min_y, max_y = min(min_y, y), max(max_y, y)
        min_z, max_z = min(min_z, z), max(max_z, z)
        found_any = True

    try:
        # Resolve path
        actual_path = part_path
        if not actual_path.exists():
            from validator.config import get_parts_dir, get_p_dir
            candidates = [
                 get_parts_dir() / part_path.name,
                 get_p_dir() / part_path.name,
                 get_parts_dir() / "s" / part_path.name,
                 get_p_dir() / "48" / part_path.name
            ]
            for c in candidates:
                if c.exists():
                    actual_path = c
                    break
            else:
                return None

        with open(actual_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.split()
                if not parts: continue
                line_type = parts[0]
                
                if line_type in ('3', '4'):
                     # Transform and update
                     # 3: x1 y1 z1 x2 y2 z2 x3 y3 z3
                     # 4: x1 y1 z1 ... x4 y4 z4
                     coords = []
                     try:
                         for i in range(2, len(parts), 3):
                             if i+2 < len(parts):
                                 lx, ly, lz = float(parts[i]), float(parts[i+1]), float(parts[i+2])
                                 coords.append((lx, ly, lz))
                     except ValueError: continue
                     
                     cpx, cpy, cpz = current_pos
                     cr11, cr12, cr13, cr21, cr22, cr23, cr31, cr32, cr33 = current_rot
                     
                     for lx, ly, lz in coords:
                         # Apply transform
                         rx = cr11*lx + cr12*ly + cr13*lz
                         ry = cr21*lx + cr22*ly + cr23*lz
                         rz = cr31*lx + cr32*ly + cr33*lz
                         update(cpx + rx, cpy + ry, cpz + rz)
                         
                elif line_type == '1':
                     cmd = parse_line(line)
                     if not cmd: continue
                     
                     sub_file = cmd.file.lower().replace('\\', '/')
                     
                     # Calculate new transform for recursion
                     lpx, lpy, lpz = cmd.pos
                     cpx, cpy, cpz = current_pos
                     cr11, cr12, cr13, cr21, cr22, cr23, cr31, cr32, cr33 = current_rot
                     
                     rx = cr11*lpx + cr12*lpy + cr13*lpz
                     ry = cr21*lpx + cr22*lpy + cr23*lpz
                     rz = cr31*lpx + cr32*lpy + cr33*lpz
                     new_pos = (cpx + rx, cpy + ry, cpz + rz)
                     
                     lr11, lr12, lr13, lr21, lr22, lr23, lr31, lr32, lr33 = cmd.rot
                     new_rot = (
                        cr11*lr11 + cr12*lr21 + cr13*lr31,
                        cr11*lr12 + cr12*lr22 + cr13*lr32,
                        cr11*lr13 + cr12*lr23 + cr13*lr33,
                        cr21*lr11 + cr22*lr21 + cr23*lr31,
                        cr21*lr12 + cr22*lr22 + cr23*lr32,
                        cr21*lr13 + cr22*lr23 + cr23*lr33,
                        cr31*lr11 + cr32*lr21 + cr33*lr31,
                        cr31*lr12 + cr32*lr22 + cr33*lr32,
                        cr31*lr13 + cr32*lr23 + cr33*lr33
                     )
                     
                     # Recurse
                     # We recurse for EVERYTHING now to get accurate bounds?
                     # Yes, traversing the whole scene graph.
                     # Limit depth via visited.
                     
                     sub_bounds = calculate_bounds_recursive(Path(sub_file), new_pos, new_rot, visited.copy())
                     if sub_bounds:
                         update(sub_bounds[0], sub_bounds[2], sub_bounds[4]) # min
                         update(sub_bounds[1], sub_bounds[3], sub_bounds[5]) # max

    except Exception:
        pass
        
    return (min_x, max_x, min_y, max_y, min_z, max_z) if found_any else None


def extract_part_data(part_path: Path) -> Tuple[Optional[PartInfo], Optional[str]]:
    """
    Extract studs, bounds, and technic holes from a single part file.
    Returns (PartInfo, list[(prim_file, pos, rot_matrix)], skip_reason).
    """
    part_id = part_path.stem
    
    
    studs = []
    technic_holes = []
    primitive_instances = [] # List of (filename, pos, rot_matrix)
    metadata = []
    subparts = []
    min_x, max_x = float('inf'), float('-inf')
    min_y, max_y = float('inf'), float('-inf')
    min_z, max_z = float('inf'), float('-inf')
    
    def update_bounds(x, y, z):
        nonlocal min_x, max_x, min_y, max_y, min_z, max_z
        min_x, max_x = min(min_x, x), max(max_x, x)
        min_y, max_y = min(min_y, y), max(max_y, y)
        min_z, max_z = min(min_z, z), max(max_z, z)
    
    try:
        with open(part_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.split()
                if not parts:
                    continue
                line_type = parts[0]
                
                if line_type == '1':
                    cmd = parse_line(line)
                    if not cmd:
                        continue
                    sub_file = cmd.file.lower().replace('\\', '/')
                    sub_id = sub_file.removesuffix('.dat').removesuffix('.ldr')
                    subparts.append(sub_id)
                    
                    # Check for stud primitives
                    if sub_file in STUD_PRIMITIVES:
                        studs.append(cmd.pos)
                        update_bounds(*cmd.pos)
                        # primitive_instances.append((sub_file, cmd.pos, cmd.rot)) # Don't add here, use recursive later
                    
                    # Check for technic hole primitives
                    if sub_file in TECHNIC_HOLE_PRIMITIVES:
                        technic_holes.append(cmd.pos)
                        update_bounds(*cmd.pos)
                        # primitive_instances.append((sub_file, cmd.pos, cmd.rot)) # Don't add here, use recursive later
                
                elif line_type == '0':
                    # Meta command
                    line_content = line.strip()
                    if line_content.startswith('0 !'):
                        metadata.append(line_content[2:].strip())
                
                elif line_type in ('3', '4'):  # Triangles and quads
                    for idx in range(2, len(parts) - 2, 3):
                        try:
                            x, y, z = float(parts[idx]), float(parts[idx+1]), float(parts[idx+2])
                            update_bounds(x, y, z)
                        except (ValueError, IndexError):
                            pass
    except Exception as e:
        part_name = get_part_name(part_path)
        return PartInfo(
            part_id=part_id,
            part_name=part_name,
            type=get_part_type(part_name),
            category=get_ldraw_category(part_path),
            ldraw_org=get_ldraw_org(part_path),
            height=0,
            bounds={},
            studs=[],
            anti_studs=[],
            technic_holes=[],
            extraction_status="failed",
            metadata=[],
            subparts=[],
            parents=[]
        ), [], f"error: {str(e)}"
    
    # Handle no geometry found
    if min_x == float('inf'):
        min_x, max_x, min_y, max_y, min_z, max_z = 0, 0, 0, 0, 0, 0
    
    # NEW: Recursive bounds if partial
    # If the file is mostly subparts, we might have missed the extent.
    # We should trust the recursive scan for bounds?
    # Actually, simpler: let's do a recursive pass for bounds just like primitives.
    
    height = max_y - min_y if max_y > min_y else 0
    bounds = {
        "x": (min_x, max_x),
        "y": (min_y, max_y),
        "z": (min_z, max_z)
    }
    
    # Generate anti-studs (project studs to bottom)
    anti_studs = [(s[0], max_y, s[2]) for s in studs] if studs else []
    
    # Determine status
    if studs or technic_holes:
        status = "success"
    elif bounds["x"] != (0, 0):
        status = "partial"
    else:
        status = "failed"
    
    part_name = get_part_name(part_path)
    return PartInfo(
        part_id=part_id,
        part_name=part_name,
        type=get_part_type(part_name),
        category=get_ldraw_category(part_path),
        ldraw_org=get_ldraw_org(part_path),
        height=height,
        bounds=bounds,
        studs=studs,
        anti_studs=anti_studs,
        technic_holes=technic_holes,
        extraction_status=status,
        metadata=metadata,
        subparts=list(set(subparts)),  # Unique subparts
        parents=[]
    ), [], None  # Return empty primitives here, we calculate them in process_part



def process_part(part_path: str) -> dict:
    """Wrapper for multiprocessing (returns dict for pickling)."""
    result, _, skip_reason = extract_part_data(Path(part_path)) # Ignore local primitives
    
    # Calculate recursive primitives AND bounds
    primitives = []
    recursive_bounds = None
    
    if result:
         try:
             # We need a new recursive function that does both, or just another pass
             # Let's add calculate_bounds_recursive
             rb = calculate_bounds_recursive(Path(part_path), (0,0,0), (1,0,0,0,1,0,0,0,1), set())
             if rb:
                 # Merge with local bounds
                 lx_min, lx_max = result.bounds['x']
                 ly_min, ly_max = result.bounds['y']
                 lz_min, lz_max = result.bounds['z']
                 
                 # If local bounds were 0 (empty), just use recursive
                 if lx_min == 0 and lx_max == 0 and ly_min == 0 and ly_max == 0:
                      result.bounds['x'] = (rb[0], rb[1])
                      result.bounds['y'] = (rb[2], rb[3])
                      result.bounds['z'] = (rb[4], rb[5])
                 else:
                      result.bounds['x'] = (min(lx_min, rb[0]), max(lx_max, rb[1]))
                      result.bounds['y'] = (min(ly_min, rb[2]), max(ly_max, rb[3]))
                      result.bounds['z'] = (min(lz_min, rb[4]), max(lz_max, rb[5]))

             primitives = find_primitives_recursive(Path(part_path), (0,0,0), (1,0,0,0,1,0,0,0,1), set())
         except Exception:
             pass
    
    if result:
        # --- Shadow Library Integration ---
        # Initialize parser relative to the project root
        project_root = Path(__file__).parent.parent
        shadow_lib_path = project_root / "data" / "offLibShadow"
        
        shadow_parser = ShadowParser(str(shadow_lib_path))
        
        # 1. Get explicit connections for the part itself (e.g. tubes)
        relative_path = f"parts/{result.part_id}.dat"
        connection_points = shadow_parser.parse_part(relative_path)
        
        if not connection_points:
             # Try p/ folder if not found
             relative_path = f"p/{result.part_id}.dat"
             connection_points = shadow_parser.parse_part(relative_path)
             
        # 2. Get connections from primitives (e.g. studs)
        for prim_file, prim_pos, prim_matrix in primitives:
             # Look up primitive shadow info (e.g. p/stud.dat)
             # Primitives are usually in p/
             prim_shadow_path = f"p/{prim_file}"
             prim_points = shadow_parser.parse_part(prim_shadow_path)
             
             # If not found in p/, try parts/ (unlikely for primitives but possible)
             if not prim_points:
                 prim_shadow_path = f"parts/{prim_file}"
                 prim_points = shadow_parser.parse_part(prim_shadow_path)
                 
             if prim_points:
                 # Transform primitive points to part space
                 for pp in prim_points:
                     # Copy to avoid mutating cache
                     new_cp = pp.copy()
                     # Transform position: part_matrix * local_pos + part_pos
                     local_pos = pp['pos']
                     
                     # Apply rotation
                     rx = prim_matrix[0]*local_pos[0] + prim_matrix[1]*local_pos[1] + prim_matrix[2]*local_pos[2]
                     ry = prim_matrix[3]*local_pos[0] + prim_matrix[4]*local_pos[1] + prim_matrix[5]*local_pos[2]
                     rz = prim_matrix[6]*local_pos[0] + prim_matrix[7]*local_pos[1] + prim_matrix[8]*local_pos[2]
                     
                     new_cp['pos'] = [rx + prim_pos[0], ry + prim_pos[1], rz + prim_pos[2]]
                     
                     # TODO: Transform orientation
                     
                     connection_points.append(new_cp)

        # Update PartInfo with recursively found primitives
        result.studs = [p[1] for p in primitives if p[0] in STUD_PRIMITIVES]
        result.technic_holes = [p[1] for p in primitives if p[0] in TECHNIC_HOLE_PRIMITIVES]

        # Extract unique connection types for filtering
        connection_types = sorted(list(set(cp['type'] for cp in connection_points)))
        
        return {
            "success": True,
            "part_id": result.part_id,
            "part_name": result.part_name,
            "type": result.type,
            "category": result.category,
            "ldraw_org": result.ldraw_org,
            "height": result.height,
            "bounds": result.bounds,
            "studs": result.studs,
            "anti_studs": result.anti_studs,
            "technic_holes": result.technic_holes,
            "extraction_status": result.extraction_status,
            "metadata": result.metadata,
            "subparts": result.subparts,
            "parents": result.parents,
            "connection_points": connection_points,
            "connection_types": connection_types
        }
    return {"success": False, "part_id": Path(part_path).stem, "reason": skip_reason}


def main():
    print("=" * 60)
    print("LDraw Catalog Builder")
    print("=" * 60)
    
    # Find all part files
    parts_dir = get_parts_dir()
    if not parts_dir.exists():
        print(f"ERROR: Parts directory not found: {parts_dir}")
        return
    
    part_files = list(parts_dir.glob("*.dat"))
    print(f"Found {len(part_files)} part files")
    
    # Initialize database
    conn = init_db()
    print(f"Database: {DB_PATH}")
    
    # Process in parallel
    num_workers = max(1, cpu_count() - 1)
    print(f"Processing with {num_workers} workers...")
    
    processed = 0
    skipped_info = [] # List of (part_id, reason)
    
    all_results = []
    with Pool(num_workers) as pool:
        part_paths = [str(p) for p in part_files]
        
        for i, result in enumerate(pool.imap_unordered(process_part, part_paths, chunksize=100)):
            if result["success"]:
                # Only save parts that have at least some geometry/bounds
                if result.get("extraction_status") != "failed":
                    all_results.append(result)
                    processed += 1
                else:
                    skipped_info.append((result["part_id"], "extraction_failed (no geometry/studs)"))
            else:
                skipped_info.append((result["part_id"], result["reason"]))
            
            if (i + 1) % 1000 == 0:
                print(f"  Extraction progress: {i + 1}/{len(part_files)} ({processed} extracted, {len(skipped_info)} skipped)")
    
    # Log skipped parts
    skipped_log_path = Path("build_catalog_skipped.log")
    with open(skipped_log_path, "w", encoding="utf-8") as f:
        for pid, reason in sorted(skipped_info):
            f.write(f"{pid}: {reason}\n")
    print(f"Logged {len(skipped_info)} skipped parts to {skipped_log_path}")

    print(f"Extraction complete. Building parent mapping for {len(all_results)} parts...")
    
    # 1. Map subparts to their parents
    parent_map = {} # subpart_id -> list of parent_ids
    for res in all_results:
        parent_id = res["part_id"]
        for sub_id in res["subparts"]:
            if sub_id not in parent_map:
                parent_map[sub_id] = []
            parent_map[sub_id].append(parent_id)
            
    # 2. Assign parents back to results
    for res in all_results:
        part_id = res["part_id"]
        res["parents"] = sorted(list(set(parent_map.get(part_id, []))))
    
    print("Saving to database...")
    for i, res in enumerate(all_results):
        # Remove success key before passing to PartInfo
        res_copy = dict(res)
        del res_copy["success"]
        part_info = PartInfo(**res_copy)
        save_part(conn, part_info)
        
        if (i + 1) % 1000 == 0:
            conn.commit()
            print(f"  Save progress: {i + 1}/{len(all_results)}")
    
    conn.commit()
    conn.close()
    
    print()
    print("=" * 60)
    print(f"Complete! Processed {processed} parts, skipped {len(skipped_info)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
