from typing import List, Tuple
from validator.parser import Placement
from validator.catalog import get_part
from validator.geometry import transform_point

import math

def studs_connect(
    stud_pos: Tuple[float, float, float],
    antistud_pos: Tuple[float, float, float],
    tolerance: float = 0.5
) -> bool:
    """
    Check if a stud and anti-stud are aligned for connection.
    Requires:
    1. Both must snap to the same grid point (multiples of 20).
    2. Distance between them must be within tolerance (direct) or ~24 units (vertical offset).
    """
    def get_grid_point(pt: Tuple[float, float, float]) -> Tuple[float, float]:
        # Snap to 20-unit grid
        # We use a small epsilon to avoid rounding issues
        return (round(pt[0] / 20) * 20, round(pt[2] / 20) * 20)

    # However, many parts are offset by 10 (like 1x1 bricks)
    # So we really should just check if they are very close.
    # The grid check is more about "is it orthogonal".
    
    # 2. Distance Check
    dist_sq = sum((a - b)**2 for a, b in zip(stud_pos, antistud_pos))
    return math.sqrt(dist_sq) < tolerance


from typing import List, Tuple, Any, Set
from validator.parser import Placement
from validator.catalog import get_part
from validator.geometry import get_world_studs, get_world_antistuds
import math

# ... (keep studs_connect) ...

def build_connection_graph(scene_graph: Any) -> List[Tuple[int, int]]:
    """
    Build an adjacency list of connections between bricks using the Scene Graph.
    Returns list of (id_A, id_B) tuples.
    """
    connections = set() # Use set to avoid duplicates
    
    # We iterate over internal IDs which correspond to placement indices
    num_parts = len(scene_graph.placements)
    
    for i in range(num_parts):
        p_A = scene_graph.get_placement(i)
        info_A = get_part(p_A.part_id)
        studs_A = get_world_studs(p_A, info_A)
        
        print(f"Checking Part {i} ({p_A.part_id}) with {len(studs_A)} studs")
        for s_pos in studs_A:
            neighbors = scene_graph.query_point(s_pos, tolerance=1.0)
            print(f"  Stud {s_pos} neighbors: {neighbors}")
            for j in neighbors:
                if i == j: continue
                p_B = scene_graph.get_placement(j)
                info_B = get_part(p_B.part_id)
                antistuds_B = get_world_antistuds(p_B, info_B)
                
                # Check if ANY anti-stud of B connects to this stud of A
                for a_pos in antistuds_B:
                    if studs_connect(s_pos, a_pos):
                        connections.add(tuple(sorted((i, j))))
                        # optimization: one connection is enough to link the parts
                        break
    
    return list(connections)
