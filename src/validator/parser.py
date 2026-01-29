from pathlib import Path
from dataclasses import dataclass, field
from typing import Iterator, Optional


@dataclass
class LDrawCommand:
    line_type: int
    color: int = 0
    pos: tuple[float, float, float] = (0, 0, 0)
    rot: tuple[float, ...] = (1, 0, 0, 0, 1, 0, 0, 0, 1)
    file: str = ""
    # For line type 0 (comment), 2 (line), 3 (triangle), 4 (quad), 5 (optional line)
    params: list[str] = field(default_factory=list)

@dataclass
class Placement:
    part_id: str
    color: int
    position: tuple[float, float, float]
    rotation: tuple[float, ...]

def parse_line(line: str) -> Optional[LDrawCommand]:
    parts = line.strip().split()
    if not parts:
        return None
    
    try:
        line_type = int(parts[0])
    except ValueError:
        return None  # Or treat as comment (0)

    cmd = LDrawCommand(line_type=line_type)

    if line_type == 1: # Sub-file reference
        if len(parts) < 15: return None
        cmd.color = int(parts[1])
        cmd.pos = (float(parts[2]), float(parts[3]), float(parts[4]))
        cmd.rot = tuple(float(p) for p in parts[5:14])
        cmd.file = " ".join(parts[14:]) # filenames can have spaces
    elif line_type == 0: # Meta/Comment
        cmd.params = parts[1:]
    
    return cmd

@dataclass
class Model:
    name: str
    placements: list[Placement] = field(default_factory=list)

def parse_mpd(file_path: Path) -> dict[str, Model]:
    """
    Parse an MPD file (or single LDraw file) and return all models contained within.
    """
    models: dict[str, Model] = {}
    current_model = Model(name="main", placements=[])
    # For non-MPD files, we treat everything as one "main" model.
    is_mpd = False
    
    with open(file_path, 'r') as f:
        for line in f:
            cmd = parse_line(line)
            if not cmd:
                continue
            
            if cmd.line_type == 0:
                # Meta command
                if cmd.params and cmd.params[0] == "FILE":
                    is_mpd = True
                    model_name = " ".join(cmd.params[1:]).lower()
                    current_model = Model(name=model_name, placements=[])
                    models[model_name] = current_model
                elif cmd.params and cmd.params[0] == "NOFILE":
                    # End of current file block
                    pass
            
            elif cmd.line_type == 1:
                # Type 1: Sub-file reference
                part_id = cmd.file.lower()
                part_id = part_id.removesuffix('.dat').removesuffix('.ldr')
                
                current_model.placements.append(Placement(
                    part_id=part_id,
                    color=cmd.color,
                    position=cmd.pos,
                    rotation=cmd.rot
                ))

    # If it wasn't an MPD file (no FILE commands), add the implicit main model
    if not is_mpd and "main" not in models:
        models["main"] = current_model
        
    return models

def parse_ldraw(file_path: Path) -> list[Placement]:
    """
    Parse an LDraw file (MOC). Handles basic LDraw and MPD (returns the first model).
    """
    models = parse_mpd(file_path)
    if not models:
        return []
    
    # Return the first model's placements.
    # Note: Dictionary order is insertion-ordered in Python 3.7+
    # If MPD, the first model usually is the main assembly.
    return list(models.values())[0].placements