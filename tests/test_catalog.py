import pytest
from validator.catalog_db import get_part, STUD_PRIMITIVES

class TestCatalogUnits:
    def test_stud_primitives_detection(self):
        # Ensure primitive names match what we expect
        assert "stud.dat" in STUD_PRIMITIVES
        assert "stud3.dat" in STUD_PRIMITIVES

    def test_get_part_basic(self):
        # 3001 is a 2x4 brick. Should have 8 studs.
        info = get_part("3001")
        print(f"3001 studs: {info.studs}")
        assert info.name == "3001"
        assert len(info.studs) == 8
        # Standard LDraw brick studs are at Y=0.0
        assert any(abs(s[1]) < 0.1 for s in info.studs)
        
    def test_get_part_tile(self):
        # 3069b is a 1x2 tile. Should have 0 studs.
        info = get_part("3069b")
        assert len(info.studs) == 0

    def test_anti_stud_heuristic(self):
        # 3001 2x4 brick. Studs at y=-24. Anti-studs should be at y=0.
        info = get_part("3001")
        # Just check one
        if info.studs:
            s = info.studs[0]
            # Find corresponding anti-stud
            matching_anti = [a for a in info.anti_studs if a[0] == s[0] and a[2] == s[2]]
            assert matching_anti, "Should have explicit or heuristic anti-stud below stud"
            assert matching_anti[0][1] == 24.0
