from typing import List, Optional, Tuple
from rtree import index
from validator.parser import Placement
from validator.catalog_db import get_part, PartInfo
from validator.geometry import get_world_aabb

class SceneGraph:
    def __init__(self):
        self.placements: List[Placement] = []
        p = index.Property()
        p.dimension = 3
        self.index = index.Index(properties=p)
        self._next_id = 0

    def add_placement(self, placement: Placement) -> int:
        """
        Add a placement to the scene graph and spatial index.
        Returns the internal ID of the added placement.
        """
        pid = self._next_id
        self._next_id += 1
        
        self.placements.append(placement)
        
        # Calculate AABB for spatial indexing
        (min_x, min_y, min_z), (max_x, max_y, max_z) = get_world_aabb(placement)
        
        # Rtree expects (minx, miny, maxx, maxy) for 2D or (minx, miny, minz, maxx, maxy, maxz) for 3D
        # We need to ensure we are using 3D if we want Z queries
        # But standard rtree properties might default to 2D. 
        # For simplicity in this POC, we can use 3D coordinates.
        
        self.index.insert(pid, (min_x, min_y, min_z, max_x, max_y, max_z))
        
        return pid

    def get_placement(self, pid: int) -> Placement:
        return self.placements[pid]

    def query_box(self, min_pt: Tuple[float, float, float], max_pt: Tuple[float, float, float]) -> List[int]:
        """
        Find all placements that intersect with the given bounding box.
        """
        return list(self.index.intersection((
            min_pt[0], min_pt[1], min_pt[2],
            max_pt[0], max_pt[1], max_pt[2]
        )))

    def query_point(self, point: Tuple[float, float, float], tolerance: float = 0.1) -> List[int]:
        """
        Find all placements near a point.
        """
        p_min = (point[0] - tolerance, point[1] - tolerance, point[2] - tolerance)
        p_max = (point[0] + tolerance, point[1] + tolerance, point[2] + tolerance)
        return self.query_box(p_min, p_max)

    def __len__(self):
        return len(self.placements)
