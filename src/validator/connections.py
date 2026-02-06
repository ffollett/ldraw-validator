from typing import List, Tuple, Set, Any, Dict
import math
from validator.parser import Placement
from validator.catalog_db import get_part, PartInfo
from validator.geometry import transform_point

def get_world_connection_points(placement: Placement, info: PartInfo) -> List[Dict[str, Any]]:
    """
    Transform all connection points of a part to world space.
    """
    if not info or not info.connection_points:
        return []
    
    world_points = []
    for cp in info.connection_points:
        # cp is a dict with 'pos', 'ori', 'type', 'gender', etc.
        local_pos = tuple(cp['pos'])
        world_pos = transform_point(local_pos, placement)
        
        # TODO: Transform orientation as well if we want strict vector matching
        # For now, we store world position and metadata
        wp = cp.copy()
        wp['world_pos'] = world_pos
        world_points.append(wp)
        
    return world_points

def check_explicit_connection(
    cp_a: Dict[str, Any],
    cp_b: Dict[str, Any],
    tolerance: float = 0.5
) -> bool:
    """
    Check if two connection points are compatible and aligned.
    """
    # 1. Gender Check: Must be M+F or F+M
    # We ignore U (Universal) or other types for strict snapping unless specified
    g_a = cp_a.get('gender')
    g_b = cp_b.get('gender')
    
    if g_a == g_b:
        # print(f"Reject Gender: {g_a} == {g_b}")
        return False # M-M or F-F is invalid (usually)
    if {g_a, g_b} != {'M', 'F'}:
        # If one is None or U, we might be lenient, but PRD said strict M+F
        # Let's start with strict M+F check to avoid false positives
        # print(f"Reject Set: {g_a}, {g_b}")
        return False
        
    # 2. Type Check: simple equality for now (CYL-CYL, etc.)
    # SNAP_CYL, SNAP_FGR, SNAP_GEN
    if cp_a.get('type') != cp_b.get('type'):
        # print(f"Reject Type: {cp_a.get('type')} != {cp_b.get('type')}")
        return False
    
    # 3. Position Check
    pos_a = cp_a['world_pos']
    pos_b = cp_b['world_pos']
    
    dist_sq = sum((a - b)**2 for a, b in zip(pos_a, pos_b))
    if dist_sq > tolerance * tolerance:
        # print(f"Reject Dist: {dist_sq}")
        return False
        
    # 4. Orientation Check (Optional/TODO)
    # If we implement this, we need to check if vectors are compatible.
    
    return True

def build_connection_graph(scene_graph: Any) -> List[Tuple[int, int]]:
    """
    Build an adjacency list of connections using explicit shadow library data.
    """
    connections = set()
    num_parts = len(scene_graph.placements)
    
    # Pre-calculate world points for all parts to avoid re-transforming
    # Map: index -> list of world connection points
    part_connections = {}
    
    for i in range(num_parts):
        p = scene_graph.get_placement(i)
        info = get_part(p.part_id)
        if info:
            part_connections[i] = get_world_connection_points(p, info)
        else:
            part_connections[i] = []

    # Iterate
    for i in range(num_parts):
        points_a = part_connections[i]
        if not points_a:
            continue
            
        # We can still use the spatial query for optimization
        # Collect all points of A
        # Query neighbors for each point
        
        for cp_a in points_a:
            w_pos = cp_a['world_pos']
            neighbors = scene_graph.query_point(w_pos, tolerance=1.0)
            # print(f"Point A {cp_a['type']} {cp_a['gender']} at {w_pos} -> Neighbors: {neighbors}")
            
            for j in neighbors:
                if i == j: continue
                # We interpret (i, j) as a potential connection
                # Check explicit compatibility against ALL points of B
                # (Optimization: spatial query returns parts close to w_pos, 
                # but we need to find the specific connection point on B that is close)
                
                points_b = part_connections[j]
                
                # Scan B's points for a match
                # This is O(N_points_A * N_points_B) locally, which is fine (usually < 100 points)
                for cp_b in points_b:
                    if check_explicit_connection(cp_a, cp_b):
                        connections.add(tuple(sorted((i, j))))
                        # Optimization: one connection enough to link graph nodes?
                        # Yes, unless we want to count strength.
                        break
                else:
                    continue # Continue inner loop if no break
                break # Break outer loop (neighbors) if connection found to j
                
    return list(connections)
