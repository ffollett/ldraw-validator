from pathlib import Path
from typing import Dict, Optional
from validator.scene_graph import SceneGraph
from validator.parser import parse_mpd, Model, Placement
from validator.geometry import multiply_matrix, transform_point_by_matrix

class Loader:
    def __init__(self, scene_graph: SceneGraph):
        self.sg = scene_graph
        self.models: Dict[str, Model] = {}

    def load(self, file_path: Path):
        """
        Load an LDraw file (single or MPD) into the scene graph.
        """
        self.models = parse_mpd(file_path)
        
        # Identify main model
        # 1. First model in the dict?
        # 2. Or explicit 'main' if not MPD?
        if not self.models:
            return
            
        # Heuristic: The first model defined is usually the main assembly
        main_model_name = list(self.models.keys())[0]
        main_model = self.models[main_model_name]
        
        print(f"[INFO] Loading main model: {main_model_name}")
        self._instantiate_model(main_model)

    def _instantiate_model(
        self, 
        model: Model, 
        parent_pos: tuple[float, float, float] = (0, 0, 0),
        parent_rot: tuple[float, ...] = (1, 0, 0, 0, 1, 0, 0, 0, 1)
    ):
        for place in model.placements:
            # Check if this placement refers to another internal model
            # LDraw names are case insensitive usually, parser lowercased them.
            # Filenames might have extension or not.
            
            # Sub-model resolution logic:
            # 1. Exact match
            # 2. Match with .ldr appened
            # 3. Match with .dat appended
            
            sub_id = place.part_id.lower()
            sub_model = self._resolve_submodel(sub_id)
            
            # Calculate world transform for this placement
            # World_Rot = Parent_Rot * Place_Rot
            world_rot = multiply_matrix(parent_rot, place.rotation)
            
            # World_Pos = Parent_Pos + (Parent_Rot * Place_Pos)
            rotated_offset = transform_point_by_matrix(place.position, parent_rot)
            world_pos = (
                parent_pos[0] + rotated_offset[0],
                parent_pos[1] + rotated_offset[1],
                parent_pos[2] + rotated_offset[2]
            )
            
            if sub_model:
                # Recurse
                self._instantiate_model(sub_model, world_pos, world_rot)
            else:
                # It's a leaf part (library brick)
                # Add to Scene Graph with resolved world coordinates
                
                # Note: SceneGraph stores Placements. We are storing a "Flattened" placement here.
                flat_placement = Placement(
                    part_id=place.part_id,
                    color=place.color,
                    position=world_pos,
                    rotation=world_rot
                )
                self.sg.add_placement(flat_placement)

    def _resolve_submodel(self, name: str) -> Optional[Model]:
        # Try exact
        if name in self.models: return self.models[name]
        # Try adding extensions
        if f"{name}.ldr" in self.models: return self.models[f"{name}.ldr"]
        if f"{name}.dat" in self.models: return self.models[f"{name}.dat"]
        # Try removing extensions?
        # If name is "sub.ldr" and key is "sub" (unlikely given parser logic but possible)
        return None
