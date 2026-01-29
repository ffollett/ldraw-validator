import pytest
from validator.parser import parse_line, parse_mpd, LDrawCommand

class TestParserUnits:
    def test_parse_line_part(self):
        line = "1 4 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat"
        cmd = parse_line(line)
        assert cmd.line_type == 1
        assert cmd.color == 4
        assert cmd.pos == (0, 0, 0)
        assert cmd.rot == (1, 0, 0, 0, 1, 0, 0, 0, 1)
        assert cmd.file == "3001.dat"
    
    def test_parse_line_meta(self):
        line = "0 FILE main.ldr"
        cmd = parse_line(line)
        assert cmd.line_type == 0
        assert cmd.params == ["FILE", "main.ldr"]

    def test_parse_line_comment_only(self):
        line = "0 // This is a comment"
        cmd = parse_line(line)
        assert cmd.line_type == 0
        
    def test_parse_bad_line(self):
        line = "INVALID LINE"
        cmd = parse_line(line)
        assert cmd is None

    def test_mpd_parsing(self, tmp_path):
        # Create a temp MPD file
        d = tmp_path / "test.mpd"
        d.write_text("""0 FILE main.ldr
1 7 0 0 0 1 0 0 0 1 0 0 0 1 sub.ldr
0 NOFILE
0 FILE sub.ldr
1 4 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat
0 NOFILE
""")
        models = parse_mpd(d)
        assert "main.ldr" in models
        assert "sub.ldr" in models
        assert len(models["main.ldr"].placements) == 1
        assert len(models["sub.ldr"].placements) == 1
