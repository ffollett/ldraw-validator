from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ValidationError:
    error_type: str  # "ungrounded", "collision", "parse_error"
    message: str
    brick_indices: list[int] = field(default_factory=list)


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    
    @classmethod
    def valid(cls) -> "ValidationResult":
        return cls(is_valid=True)
    
    @classmethod
    def invalid(cls, errors: list[ValidationError]) -> "ValidationResult":
        return cls(is_valid=False, errors=errors)


from .parser import parse_ldraw, Placement
from .parser import parse_ldraw, Placement
from .collision import check_collisions
from .connections import build_connection_graph
from .grounding import validate_grounding
from .scene_graph import SceneGraph
from .loader import Loader
from .renderer import render_scene

def validate_moc(file_path: Path) -> ValidationResult:
    """
    Validate a LEGO MOC file.
    """
    sg = SceneGraph()
    loader = Loader(sg)
    try:
        loader.load(file_path)
    except Exception as e:
        return ValidationResult.invalid([
            ValidationError(error_type="parse_error", message=str(e))
        ])
    
    placements = sg.placements
    if not placements:
        return ValidationResult.valid()
        
    errors = []
    
    # 1. Check Collisions
    # Use Scene Graph for collision check optimization
    collisions = check_collisions(sg)
    for i, j in collisions:
        errors.append(ValidationError(
            error_type="collision",
            message=f"Collision between brick {i} and {j}",
            brick_indices=[i, j]
        ))
    
    # 1.5. Check Grid Alignment
    from validator.checks import validate_grid_alignment
    from validator.catalog import get_part
    
    for i, p in enumerate(placements):
        try:
            part_info = get_part(p.part_id)
            warnings = validate_grid_alignment(p, part_info)
            for w in warnings:
                errors.append(ValidationError(
                    error_type="grid_alignment",
                    message=f"Part {i} ({p.part_id}): {w}",
                    brick_indices=[i]
                ))
        except KeyError:
             pass 

    # 2. Build connection graph
    # Returns List[Tuple[int, int]]
    connections = build_connection_graph(sg)
    
    # 3. Check Grounding
    is_grounded, floating_parts = validate_grounding(placements, connections)
    
    for i in floating_parts:
        errors.append(ValidationError(
            error_type="ungrounded",
            message=f"Part {i} is not connected to ground",
            brick_indices=[i]
        ))
            
    if errors:
        return ValidationResult.invalid(errors)
        
    return ValidationResult.valid()
