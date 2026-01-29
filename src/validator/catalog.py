from dataclasses import dataclass
from typing import Optional, Set, List, Tuple, Any
from pathlib import Path
from validator.config import get_parts_dir, get_p_dir
from validator.parser import parse_line
from validator.geometry import multiply_matrix, transform_point_by_matrix
import math
import json
import pickle

@dataclass
class PartInfo:
    name: str
    studs: list[tuple[float, float, float]]  # Stud positions in local coords
    height: float
    bounds: dict[str, tuple[float, float]]  # axis -> (min, max)
    anti_studs: list[tuple[float, float, float]] = None # Relative to TOP surface

PART_CATALOG: dict[str, PartInfo] = {}

# Common stud primitives in LDraw
STUD_PRIMITIVES = {
    "stud.dat", "stud2.dat", "stud3.dat", "stud6.dat",
    "stud10.dat", "stud12.dat", "stud15.dat", "studp01.dat", "studel.dat"
}

def resolve_part_path(part_id: str) -> Optional[Path]:
    test_id = part_id.replace('\\', '/')
    # Check parts/
    p = get_parts_dir() / f"{test_id}.dat"
    if p.exists(): return p
    
    # Check p/
    p = get_p_dir() / f"{test_id}.dat"
    if p.exists(): return p
    
    # If it has a slash, it might be in s/ or other subdirs
    if '/' in test_id:
        p = get_parts_dir() / f"{test_id}.dat"
        if p.exists(): return p
        p = get_p_dir() / f"{test_id}.dat"
        if p.exists(): return p

    return None

STUD_CACHE: dict[str, list[tuple[float, float, float]]] = {}
BOUNDS_CACHE: dict[str, Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]] = {}

def get_geometry_for_part(part_id: str) -> Tuple[List[Tuple[float, float, float]], dict]:
    """
    Returns (studs, bounds_dict)
    """
    if part_id in STUD_CACHE and part_id in BOUNDS_CACHE:
        return STUD_CACHE[part_id], {"x": BOUNDS_CACHE[part_id][0], "y": BOUNDS_CACHE[part_id][1], "z": BOUNDS_CACHE[part_id][2]}
        
    # Base case for primitives
    part_name_lower = part_id.lower()
    for prim in STUD_PRIMITIVES:
        if part_name_lower == prim or part_name_lower == prim.replace('.dat', ''):
             return [(0.0, 0.0, 0.0)], {"x": (-4, 4), "y": (0, 4), "z": (-4, 4)}

    file_path = resolve_part_path(part_id)
    if not file_path:
        return [], {"x": (0, 0), "y": (0, 0), "z": (0, 0)}

    studs = []
    min_x, max_x = float('inf'), float('-inf')
    min_y, max_y = float('inf'), float('-inf')
    min_z, max_z = float('inf'), float('-inf')

    def update_bounds(x, y, z):
        nonlocal min_x, max_x, min_y, max_y, min_z, max_z
        min_x, max_x = min(min_x, x), max(max_x, x)
        min_y, max_y = min(min_y, y), max(max_y, y)
        min_z, max_z = min(min_z, z), max(max_z, z)

    try:
        with open(file_path, 'r') as f:
            for line in f:
                parts = line.split()
                if not parts: continue
                line_type = parts[0]
                
                if line_type == '1':
                    cmd = parse_line(line)
                    if not cmd: continue
                    sub_file = cmd.file.lower().replace('\\', '/')
                    sub_id = sub_file.removesuffix('.dat').removesuffix('.ldr')
                    
                    if sub_file in STUD_PRIMITIVES:
                        studs.append(cmd.pos)
                        update_bounds(cmd.pos[0], cmd.pos[1], cmd.pos[2])
                    else:
                        sub_studs, sub_bounds_dict = get_geometry_for_part(sub_id)
                        # Transform sub studs
                        for s in sub_studs:
                            t = transform_point_by_matrix(s, cmd.rot)
                            studs.append((t[0]+cmd.pos[0], t[1]+cmd.pos[1], t[2]+cmd.pos[2]))
                        
                        # Transform sub bounds corners (approximate)
                        for sx in sub_bounds_dict['x']:
                            for sy in sub_bounds_dict['y']:
                                for sz in sub_bounds_dict['z']:
                                    t = transform_point_by_matrix((sx, sy, sz), cmd.rot)
                                    update_bounds(t[0]+cmd.pos[0], t[1]+cmd.pos[1], t[2]+cmd.pos[2])
                
                elif line_type in ('2', '3', '4', '5'):
                    # Explicit geometry
                    for idx in range(2, len(parts), 3):
                        try:
                            x, y, z = float(parts[idx]), float(parts[idx+1]), float(parts[idx+2])
                            update_bounds(x, y, z)
                        except: pass
    except Exception as e:
        print(f"Error parsing {part_id}: {e}")

    if min_x == float('inf'): # No geometry found
        min_x, max_x, min_y, max_y, min_z, max_z = 0,0,0,0,0,0
        
    STUD_CACHE[part_id] = studs
    BOUNDS_CACHE[part_id] = ((min_x, max_x), (min_y, max_y), (min_z, max_z))
    return studs, {"x": (min_x, max_x), "y": (min_y, max_y), "z": (min_z, max_z)}

def get_studs_for_part(part_id: str) -> list[tuple[float, float, float]]:
    s, _ = get_geometry_for_part(part_id)
    return s

CACHE_FILE = Path(__file__).parent / "data" / "catalog_cache.pkl"

def save_cache():
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(PART_CATALOG, f)
    print(f"[INFO] Saved {len(PART_CATALOG)} parts to cache at {CACHE_FILE}")

def load_cache():
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'rb') as f:
                data = pickle.load(f)
                PART_CATALOG.update(data)
            print(f"[INFO] Loaded {len(PART_CATALOG)} parts from cache")
        except Exception as e:
            print(f"[WARN] Failed to load cache: {e}")

# Load cache on module import
load_cache()

def load_part(part_id: str) -> PartInfo:
    if part_id in PART_CATALOG:
        return PART_CATALOG[part_id]
        
    studs, bounds = get_geometry_for_part(part_id)
    
    # If no geometry found, use fallbacks
    if bounds['x'] == (0, 0):
        if part_id == "3069b": # 1x2 tile
            bounds = {"x": (-10, 10), "y": (0, 8), "z": (-20, 20)}
        elif part_id == "3067": # 2x2 tile
            bounds = {"x": (-20, 20), "y": (0, 8), "z": (-20, 20)}
        else:
            bounds = {"x": (-10, 10), "y": (0, 24), "z": (-10, 10)}

    min_y, max_y = bounds['y']
    height = max_y - min_y
    
    # Heuristic for Anti-studs:
    # Most parts have studs at Y=0.
    # Anti-studs at the bottom (max_y).
    anti_studs = []
    if studs:
        for s in studs:
            anti_studs.append((s[0], max_y, s[2]))
    else:
        # Generate grid for common tiles if no studs
        min_x, max_x = bounds['x']
        min_z, max_z = bounds['z']
        for x in range(int(min_x + 10), int(max_x), 20):
            for z in range(int(min_z + 10), int(max_z), 20):
                anti_studs.append((float(x), max_y, float(z)))

    info = PartInfo(
        name=part_id,
        studs=studs,
        height=height,
        bounds=bounds,
        anti_studs=anti_studs
    )
    
    PART_CATALOG[part_id] = info
    return info

def get_part(part_id: str) -> PartInfo:
    return load_part(part_id)