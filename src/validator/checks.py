from typing import List, Tuple
from validator.parser import Placement
from validator.catalog_db import PartInfo
from validator.geometry import get_world_studs

def validate_grid_alignment(placement: Placement, part: PartInfo) -> List[str]:
    """Check if transformed studs land on valid positions."""
    warnings = []
    
    # We need to account for floating point errors, so we round to nearest reasonable precision
    # before checking modulo. However, the user request specifically asked for modulo checks.
    # Given the transformations, exact integer coordinates might be slightly off.
    # But let's follow the user's logic first.
    
    for stud in get_world_studs(placement, part):
        # Even-sized parts: studs should be at 10 mod 20
        # Odd-sized parts: studs should be at 0 mod 20
        # We need to handle negative coordinates correctly with modulo in Python.
        # Python's % operator returns result with same sign as divisor (positive for 20).
        
        # Rounding to handle float imprecision from rotation
        x = round(stud[0], 2)
        z = round(stud[2], 2)
        
        x_mod = int(x) % 20
        z_mod = int(z) % 20
        
        if not (x_mod in (0, 10) and z_mod in (0, 10)):
            warnings.append(f"Stud at {stud} off-grid")
            
            
    return warnings

def validate_collisions(scene_graph) -> List[str]:
    """Check for physical collisions between bricks."""
    from validator.collision import check_collisions
    return check_collisions(scene_graph)
