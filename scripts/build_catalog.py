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
from typing import Tuple, List, Optional
import re

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validator.catalog_db import init_db, save_part, PartInfo, DB_PATH
from validator.config import get_parts_dir, get_p_dir
from validator.parser import parse_line
from validator.geometry import transform_point_by_matrix

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

# Skip minifig parts
MINIFIG_PATTERNS = [
    r"^97[0-9]{2}",  # Torso patterns
    r"^3626",        # Head
    r"^3819",        # Arms
    r"^3818",        # Hands
]


def is_minifig(part_id: str) -> bool:
    """Check if part is a minifig component."""
    for pattern in MINIFIG_PATTERNS:
        if re.match(pattern, part_id):
            return True
    return False


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


def extract_part_data(part_path: Path) -> Optional[PartInfo]:
    """
    Extract studs, bounds, and technic holes from a single part file.
    Returns PartInfo or None if extraction fails.
    """
    part_id = part_path.stem
    
    # Skip minifig parts
    if is_minifig(part_id):
        return None
    
    studs = []
    technic_holes = []
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
                    
                    # Check for stud primitives
                    if sub_file in STUD_PRIMITIVES:
                        studs.append(cmd.pos)
                        update_bounds(*cmd.pos)
                    
                    # Check for technic hole primitives
                    if sub_file in TECHNIC_HOLE_PRIMITIVES:
                        technic_holes.append(cmd.pos)
                        update_bounds(*cmd.pos)
                
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
            extraction_status="failed"
        )
    
    # Handle no geometry found
    if min_x == float('inf'):
        min_x, max_x, min_y, max_y, min_z, max_z = 0, 0, 0, 0, 0, 0
    
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
        extraction_status=status
    )


def process_part(part_path: str) -> Optional[dict]:
    """Wrapper for multiprocessing (returns dict for pickling)."""
    result = extract_part_data(Path(part_path))
    if result:
        return {
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
            "extraction_status": result.extraction_status
        }
    return None


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
    skipped = 0
    
    with Pool(num_workers) as pool:
        part_paths = [str(p) for p in part_files]
        
        for i, result in enumerate(pool.imap_unordered(process_part, part_paths, chunksize=100)):
            if result:
                part_info = PartInfo(**result)
                save_part(conn, part_info)
                processed += 1
            else:
                skipped += 1
            
            # Progress update
            if (i + 1) % 1000 == 0:
                conn.commit()
                print(f"  Progress: {i + 1}/{len(part_files)} ({processed} saved, {skipped} skipped)")
    
    conn.commit()
    conn.close()
    
    print()
    print("=" * 60)
    print(f"Complete! Processed {processed} parts, skipped {skipped}")
    print("=" * 60)


if __name__ == "__main__":
    main()
