import pytest
from validator.connections import check_explicit_connection, build_connection_graph
from validator.scene_graph import SceneGraph
from validator.parser import Placement

class TestConnectionsUnits:
    def test_check_explicit_connection_aligned(self):
        # Aligned M+F
        cp_a = {'type': 'SNAP_CYL', 'gender': 'M', 'world_pos': (10, 0, 10)}
        cp_b = {'type': 'SNAP_CYL', 'gender': 'F', 'world_pos': (10, 0, 10)}
        assert check_explicit_connection(cp_a, cp_b)

    def test_check_explicit_connection_gender_mismatch(self):
        # M+M
        cp_a = {'type': 'SNAP_CYL', 'gender': 'M', 'world_pos': (10, 0, 10)}
        cp_b = {'type': 'SNAP_CYL', 'gender': 'M', 'world_pos': (10, 0, 10)}
        assert not check_explicit_connection(cp_a, cp_b)
        
    def test_check_explicit_connection_type_mismatch(self):
        # CYL+FGR
        cp_a = {'type': 'SNAP_CYL', 'gender': 'M', 'world_pos': (10, 0, 10)}
        cp_b = {'type': 'SNAP_FGR', 'gender': 'F', 'world_pos': (10, 0, 10)}
        assert not check_explicit_connection(cp_a, cp_b)
        
    def test_check_explicit_connection_too_far(self):
        # 1 unit off (tolerance usually 0.5)
        cp_a = {'type': 'SNAP_CYL', 'gender': 'M', 'world_pos': (10, 0, 10)}
        cp_b = {'type': 'SNAP_CYL', 'gender': 'F', 'world_pos': (11, 0, 10)}
        assert not check_explicit_connection(cp_a, cp_b)

    def test_build_connection_graph_simple(self):
        sg = SceneGraph()
        # Brick 1 at 0,0,0 (3003 is 2x2 brick, has connections)
        # Using 3003 because we know it works from verification
        p1 = Placement("3003", 1, (0, 0, 0), (1,0,0,0,1,0,0,0,1))
        # Brick 2 stacked on top at 0, -24, 0
        p2 = Placement("3003", 1, (0, -24, 0), (1,0,0,0,1,0,0,0,1))
        
        sg.add_placement(p1)
        sg.add_placement(p2)
        
        connections = build_connection_graph(sg)
        assert len(connections) >= 1
        # Should be (0, 1) sorted
        assert tuple(sorted((0, 1))) in connections
