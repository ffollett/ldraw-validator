from typing import List, Tuple, Set
from validator.scene_graph import SceneGraph
from validator.geometry import get_world_aabb

def check_collisions(scene_graph: SceneGraph) -> List[Tuple[int, int]]:
    """
    Check for collisions between bricks in the scene graph.
    Returns a list of (index_a, index_b) tuples for colliding pairs.
    """
    collisions = []
    
    # We will use the scene graph's broad-phase query to find potential candidates.
    # However, since we need to check *every* pair, we can iterate through all placements
    # and query the index for each one.
    
    # To avoid duplicate reports (A vs B and B vs A), we can store processed pairs.
    processed_pairs: Set[Tuple[int, int]] = set()
    
    for i in range(len(scene_graph.placements)):
        placement_a = scene_graph.get_placement(i)
        
        # Get AABB for Broad Phase
        (min_x, min_y, min_z), (max_x, max_y, max_z) = get_world_aabb(placement_a)
        
        # Query potential colliders
        # We shrink the query box slightly to avoid false positives from adjacent touching bricks?
        # Actually, if we use exact AABB, R-tree returns anything that touches or overlaps.
        # We'll filter in narrow phase.
        candidates = scene_graph.query_box((min_x, min_y, min_z), (max_x, max_y, max_z))
        
        for j in candidates:
            if i == j:
                continue
                
            # Sort IDs to ensure consistent pair ordering
            pair = tuple(sorted((i, j)))
            if pair in processed_pairs:
                continue
            
            processed_pairs.add(pair)
            placement_b = scene_graph.get_placement(j)
            
            if _check_narrow_phase(placement_a, placement_b):
                collisions.append((i, j))
                
    return collisions

def _check_narrow_phase(p1, p2) -> bool:
    """
    Detailed intersection test.
    Returns True if valid collision (volume intersection), False otherwise.
    """
    
    # 1. Exact AABB Overlap Calculation
    (min1, max1) = get_world_aabb(p1)
    (min2, max2) = get_world_aabb(p2)
    
    overlap_x = min(max1[0], max2[0]) - max(min1[0], min2[0])
    overlap_y = min(max1[1], max2[1]) - max(min1[1], min2[1])
    overlap_z = min(max1[2], max2[2]) - max(min1[2], min2[2])
    
    # If any dimension has no overlap (<= some epsilon), then no collision
    # Using a small epsilon to allow touching faces
    epsilon = 0.05 
    
    if overlap_x < epsilon or overlap_y < epsilon or overlap_z < epsilon:
        return False
        
    # 2. Stud/Anti-stud handling (Heuristic)
    # If the intersection is primarily vertical and they are stacked, we might allow it.
    # But strictly speaking, bricks shouldn't intersect unless it's the stud vs hole.
    # Logic: 
    #   - If Y-overlap is small (stud height approx 4 LDU), and X/Z overlap matches connection...
    #   - For POC, we'll just stick to AABB. If AABB overlaps significantly, it's a collision.
    #   - BUT, standard bricks stacked will have touching faces (overlap = 0 or close).
    #   - Studs go INTO the clean AABB of the brick above? 
    #   - Usually LDraw primitives for "Brick" include the studs on top.
    #   - The generic bounding box usually INCLUDES studs.
    #   - So if Brick A is on top of Brick B, Brick B's studs stick INTO Brick A's bottom.
    #   - This means their AABBs WILL intersect.
    
    # Workaround for POC Week 4:
    # We define a "Collision Box" that is slightly smaller than the visual BBox.
    # Specifically, we might ignore the top 4 LDU (stud height) of the bottom brick
    # or the bottom 4 LDU of the top brick?
    # Better: Shrink the AABB by a margin (e.g. 1 LDU) on all sides for the purpose of "Solid" collision.
    # This avoids "touching" false positives and might bypass the stud overlap if it's just studs.
    
    # Refined Check with Shrink
    shrink_amount = 2.0 # LDU. Studs are usually ~4 LDU high.
    
    s_min1 = (min1[0]+shrink_amount, min1[1]+shrink_amount, min1[2]+shrink_amount)
    s_max1 = (max1[0]-shrink_amount, max1[1]-shrink_amount, max1[2]-shrink_amount)
    
    s_min2 = (min2[0]+shrink_amount, min2[1]+shrink_amount, min2[2]+shrink_amount)
    s_max2 = (max2[0]-shrink_amount, max2[1]-shrink_amount, max2[2]-shrink_amount)
    
    # Check if SHRUNKEN boxes intersect
    s_overlap_x = min(s_max1[0], s_max2[0]) - max(s_min1[0], s_min2[0])
    s_overlap_y = min(s_max1[1], s_max2[1]) - max(s_min1[1], s_min2[1])
    s_overlap_z = min(s_max1[2], s_max2[2]) - max(s_min1[2], s_min2[2])
    
    if s_overlap_x > 0 and s_overlap_y > 0 and s_overlap_z > 0:
        return True
        
    return False
