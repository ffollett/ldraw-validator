import pytest
from validator.scene_graph import SceneGraph
from validator.parser import Placement

class TestSceneGraphUnits:
    def test_add_and_query_point(self):
        sg = SceneGraph()
        p1 = Placement("3001", 1, (0, 0, 0), (1,0,0,0,1,0,0,0,1))
        p2 = Placement("3001", 1, (100, 0, 0), (1,0,0,0,1,0,0,0,1))
        
        id1 = sg.add_placement(p1)
        id2 = sg.add_placement(p2)
        
        # Query near p1
        results = sg.query_point((5, 0, 0), tolerance=10)
        assert id1 in results
        assert id2 not in results

    def test_query_box(self):
        sg = SceneGraph()
        # Brick 2x4 is approx +/- 40 in X
        p1 = Placement("3001", 1, (0, 0, 0), (1,0,0,0,1,0,0,0,1)) 
        id1 = sg.add_placement(p1)
        
        # Box from -10 to 10
        results = sg.query_box((-10,-10,-10), (10,10,10))
        assert id1 in results
