import pytest
from pathlib import Path
from validator.shadow_parser import ShadowParser

# Mock Shadow Lib structure
@pytest.fixture
def shadow_lib(tmp_path):
    # create parts/3003.dat
    (tmp_path / "parts").mkdir()
    (tmp_path / "p").mkdir()
    
    with open(tmp_path / "parts" / "3003.dat", "w") as f:
        f.write("0 !LDCAD SNAP_CYL [gender=F] [id=left] [pos=0 0 0] [ori=1 0 0 0 1 0 0 0 1]\n")
        
    return tmp_path

def test_shadow_parser_init(shadow_lib):
    parser = ShadowParser(str(shadow_lib))
    assert parser.shadow_lib_path == str(shadow_lib)

def test_parse_part(shadow_lib):
    parser = ShadowParser(str(shadow_lib))
    points = parser.parse_part("parts/3003.dat")
    assert len(points) == 1
    assert points[0]['type'] == 'SNAP_CYL'
    assert points[0]['gender'] == 'F'

def test_parse_missing_part(shadow_lib):
    parser = ShadowParser(str(shadow_lib))
    points = parser.parse_part("parts/missing.dat")
    assert len(points) == 0
