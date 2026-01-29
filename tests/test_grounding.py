import pytest
from validator.grounding import is_touching_ground, validate_grounding
from validator.parser import Placement

class TestGroundingUnits:
    def test_is_touching_ground_simple(self):
        # Brick at -24 -> Bottom at 0
        p = Placement("3001", 1, (0, -24, 0), (1,0,0,0,1,0,0,0,1))
        assert is_touching_ground(p)

    def test_is_touching_ground_plate(self):
        # Plate at -8 -> Bottom at 0
        p = Placement("3020", 1, (0, -8, 0), (1,0,0,0,1,0,0,0,1))
        assert is_touching_ground(p)

    def test_not_touching_ground(self):
        p = Placement("3001", 1, (0, -100, 0), (1,0,0,0,1,0,0,0,1))
        assert not is_touching_ground(p)

    def test_validate_grounding_chains(self):
        # 0 is grounded. 1 connected to 0. 2 connected to 1.
        # 3 isolated.
        placements = [
            Placement("3001", 1, (0,-24,0), (1,0,0,0,1,0,0,0,1)), # 0 (Grounded)
            Placement("3001", 1, (0,-48,0), (1,0,0,0,1,0,0,0,1)), # 1 (Connected to 0)
            Placement("3001", 1, (0,-72,0), (1,0,0,0,1,0,0,0,1)), # 2 (Connected to 1)
            Placement("3001", 1, (100,-100,0), (1,0,0,0,1,0,0,0,1)), # 3 (Floating)
        ]
        connections = [(0, 1), (1, 2)]
        
        valid, floating = validate_grounding(placements, connections)
        assert not valid
        assert 3 in floating
        assert 0 not in floating
        assert 2 not in floating
