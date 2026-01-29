import pytest
from validator.connections import studs_connect, build_connection_graph
from validator.scene_graph import SceneGraph
from validator.parser import Placement

class TestConnectionsUnits:
    def test_studs_connect_logic_aligned(self):
        # Aligned
        s = (10, -24, 10)
        a = (10, -24, 10)
        assert studs_connect(s, a)

    def test_studs_connect_logic_misaligned_grid(self):
        # s on 10-grid, a on 0-grid
        s = (10, -24, 10)
        a = (0, 0, 0)
        assert not studs_connect(s, a)
        
    def test_studs_connect_logic_too_far(self):
        s = (10, -24, 10)
        a = (15, 0, 10) # 5 units off
        assert not studs_connect(s, a)

    def test_build_connection_graph_simple(self):
        sg = SceneGraph()
        # Brick 1 at 0,0,0
        p1 = Placement("3001", 1, (0, 0, 0), (1,0,0,0,1,0,0,0,1))
        # Brick 2 stacked on top at 0, -24, 0
        p2 = Placement("3001", 1, (0, -24, 0), (1,0,0,0,1,0,0,0,1))
        
        sg.add_placement(p1)
        sg.add_placement(p2)
        
        connections = build_connection_graph(sg)
        assert len(connections) >= 1
        # Should be (0, 1) or (1, 0)
        assert tuple(sorted((0, 1))) in connections
