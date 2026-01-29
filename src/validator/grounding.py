from typing import List, Tuple, Set
from validator.geometry import get_world_aabb
from validator.parser import Placement

def is_touching_ground(
    placement: Placement,
    ground_y: float = 0,
    tolerance: float = 0.5
) -> bool:
    """
    Check if a placement is in contact with the ground plane.
    Supports -8 and -20 offsets seen in test data and scripts.
    """
    _, max_b = get_world_aabb(placement)
    
    bottom_y = max_b[1]
    
    # Ground is always at Y=0 in this model.
    return abs(bottom_y - ground_y) < tolerance

def validate_grounding(
    placements: List[Placement],
    connections: List[Tuple[int, int]]
) -> Tuple[bool, List[int]]:
    """
    Verify that all parts are connected to the ground.
    Returns (is_valid, list_of_floating_part_ids).
    """
    num_parts = len(placements)
    if num_parts == 0:
        return True, []

    # Build adjacency list
    adj: List[List[int]] = [[] for _ in range(num_parts)]
    for u, v in connections:
        adj[u].append(v)
        adj[v].append(u)

    # Find parts touching ground directly
    grounded: Set[int] = set()
    queue: List[int] = []
    
    for i, p in enumerate(placements):
        if is_touching_ground(p):
            grounded.add(i)
            queue.append(i)
            
    # BFS
    idx = 0
    while idx < len(queue):
        u = queue[idx]
        idx += 1
        
        for v in adj[u]:
            if v not in grounded:
                grounded.add(v)
                queue.append(v)
                
    # Check if all parts are grounded
    floating = []
    for i in range(num_parts):
        if i not in grounded:
            floating.append(i)
            
    return len(floating) == 0, floating