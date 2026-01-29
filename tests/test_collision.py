import pytest
from validator.scene_graph import SceneGraph
from validator.parser import Placement
from validator.collision import check_collisions

class TestCollisionUnits:
    
    def test_no_collision_distant(self):
        sg = SceneGraph()
        # 3001 is 2x4 brick (approx 40x24x20 LDU)
        # Position 1: Origin
        p1 = Placement("3001", 1, (0, 0, 0), (1,0,0,0,1,0,0,0,1))
        # Position 2: Far away (100, 0, 0)
        p2 = Placement("3001", 1, (100, 0, 0), (1,0,0,0,1,0,0,0,1))
        
        sg.add_placement(p1)
        sg.add_placement(p2)
        
        collisions = check_collisions(sg)
        assert len(collisions) == 0

    def test_collision_detected_overlap(self):
        sg = SceneGraph()
        # Two bricks sharing the same space
        p1 = Placement("3001", 1, (0, 0, 0), (1,0,0,0,1,0,0,0,1))
        p2 = Placement("3001", 1, (10, 0, 0), (1,0,0,0,1,0,0,0,1)) # Only shifted 10 LDU, should overlap
        
        sg.add_placement(p1)
        sg.add_placement(p2)
        
        collisions = check_collisions(sg)
        assert len(collisions) > 0
        # Expect tuple (index1, index2)
        assert isinstance(collisions[0], tuple)
        assert len(collisions[0]) == 2

    def test_touching_bricks_ok(self):
        sg = SceneGraph()
        # 3001 is 2x4 which is 4 studs long = 80 LDU? 
        # Wait, LDU is 20 per stud width. 4 studs = 80 LDU.
        # Let's verify 3001 dimensions.
        # Catalog tests say 3001 is 2x4.
        
        # If I place them 80 units apart, they should touch but not collide.
        # Length of 2x4 brick is 80 LDU (4 * 20).
        
        p1 = Placement("3001", 1, (0, 0, 0), (1,0,0,0,1,0,0,0,1))
        p2 = Placement("3001", 1, (80, 0, 0), (1,0,0,0,1,0,0,0,1))
        
        sg.add_placement(p1)
        sg.add_placement(p2)
        
        collisions = check_collisions(sg)
        # Should be empty because they are just touching faces
        assert len(collisions) == 0

    def test_stacking_ok(self):
        sg = SceneGraph()
        # Stacking a brick on top of another.
        # Height of brick is 24 LDU.
        p1 = Placement("3001", 1, (0, 0, 0), (1,0,0,0,1,0,0,0,1))
        p2 = Placement("3001", 1, (0, -24, 0), (1,0,0,0,1,0,0,0,1)) 
        # LDraw Y is down, so -24 is UP (or above).
        # Wait, if p1 is at 0, p2 at -24 is "above" it in LDraw coords.
        # They share the face at Y=0 (top of p2, bottom of p1?)
        # Or p1 is at 0..24 (down). p2 is at -24..0.
        # They touch at 0.
        
        sg.add_placement(p1)
        sg.add_placement(p2)
        
        collisions = check_collisions(sg)
        assert len(collisions) == 0
