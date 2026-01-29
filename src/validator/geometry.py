from typing import Tuple, List, Dict, Any, Optional
from validator.parser import Placement

def multiply_matrix(m1: tuple[float, ...], m2: tuple[float, ...]) -> tuple[float, ...]:
    """
    Multiply two 3x3 matrices (tuples of 9 floats).
    Result = m1 * m2
    """
    # m1: r00 r01 r02 r10 r11 r12 r20 r21 r22
    # m2: s00 s01 s02 s10 s11 s12 s20 s21 s22
    
    # Row 0
    r00 = m1[0]*m2[0] + m1[1]*m2[3] + m1[2]*m2[6]
    r01 = m1[0]*m2[1] + m1[1]*m2[4] + m1[2]*m2[7]
    r02 = m1[0]*m2[2] + m1[1]*m2[5] + m1[2]*m2[8]
    
    # Row 1
    r10 = m1[3]*m2[0] + m1[4]*m2[3] + m1[5]*m2[6]
    r11 = m1[3]*m2[1] + m1[4]*m2[4] + m1[5]*m2[7]
    r12 = m1[3]*m2[2] + m1[4]*m2[5] + m1[5]*m2[8]
    
    # Row 2
    r20 = m1[6]*m2[0] + m1[7]*m2[3] + m1[8]*m2[6]
    r21 = m1[6]*m2[1] + m1[7]*m2[4] + m1[8]*m2[7]
    r22 = m1[6]*m2[2] + m1[7]*m2[5] + m1[8]*m2[8]
    
    return (r00, r01, r02, r10, r11, r12, r20, r21, r22)

def transform_point_by_matrix(point: Tuple[float, float, float], matrix: tuple[float, ...]) -> Tuple[float, float, float]:
    x, y, z = point
    # R * P
    nx = matrix[0]*x + matrix[1]*y + matrix[2]*z
    ny = matrix[3]*x + matrix[4]*y + matrix[5]*z
    nz = matrix[6]*x + matrix[7]*y + matrix[8]*z
    return (nx, ny, nz)

def transform_point(point: Tuple[float, float, float], placement: Placement) -> Tuple[float, float, float]:
    """
    Transform a point from local part coordinates to world coordinates.
    P_world = (Rotation * P_local) + Position
    """
    x, y, z = point
    r = placement.rotation
    px, py, pz = placement.position
    
    # R * P + T
    nx = r[0]*x + r[1]*y + r[2]*z + px
    ny = r[3]*x + r[4]*y + r[5]*z + py
    nz = r[6]*x + r[7]*y + r[8]*z + pz
    return (nx, ny, nz)


# ... (keep existing check_collision etc) ...
def get_world_studs(placement: Placement, part_info: Any) -> List[Tuple[float, float, float]]:
    return [transform_point(s, placement) for s in part_info.studs]

def get_world_antistuds(placement: Placement, part_info: Any) -> List[Tuple[float, float, float]]:
    return [transform_point(s, placement) for s in (part_info.anti_studs or [])]

def get_world_aabb(placement: Placement) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    # Avoid circular import if possible, but for AABB we need catalog info.
    # Assuming the caller has access or we pass info separately.
    # Because 'from validator.catalog import get_part' was at top level, it might cycle.
    # Moving import inside if needed.
    from validator.catalog import get_part
    info = get_part(placement.part_id)
    bx = info.bounds['x']
    by = info.bounds['y']
    bz = info.bounds['z']
    
    corners = []
    for x in bx:
        for y in by:
            for z in bz:
                corners.append(transform_point((x, y, z), placement))
                
    min_x = min(c[0] for c in corners)
    min_y = min(c[1] for c in corners)
    min_z = min(c[2] for c in corners)
    max_x = max(c[0] for c in corners)
    max_y = max(c[1] for c in corners)
    max_z = max(c[2] for c in corners)
    
    return (min_x, min_y, min_z), (max_x, max_y, max_z)

def check_collision(p1: Placement, p2: Placement, tolerance: float = 0.5) -> bool:
    min1, max1 = get_world_aabb(p1)
    min2, max2 = get_world_aabb(p2)
    
    for i in range(3):
        if max1[i] <= min2[i] + tolerance or min1[i] >= max2[i] - tolerance:
            return False
    return True
