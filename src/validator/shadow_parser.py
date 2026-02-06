import os
import re
from typing import List, Dict, Any, Optional

class ShadowParser:
    """
    Parses LDraw files (specifically shadow library files) to extract LDCad connectivity data.
    """
    
    def __init__(self, shadow_lib_path: str):
        self.shadow_lib_path = shadow_lib_path
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    def parse_part(self, part_filename: str) -> List[Dict[str, Any]]:
        """
        Parses a part file (and its dependencies) to return a list of connection points.
        The part_filename should be relative to the shadow library root (e.g. 'parts/3001.dat').
        """
        if part_filename in self._cache:
            return self._cache[part_filename]

        full_path = os.path.join(self.shadow_lib_path, part_filename)
        if not os.path.exists(full_path):
            # Try finding it in 'parts' or 'p' if not found directly, or normalize separators
            normalized = part_filename.replace('\\', os.sep).replace('/', os.sep)
            full_path = os.path.join(self.shadow_lib_path, normalized)
            
            if not os.path.exists(full_path):
                 # Try prepending 'parts' and 'p'
                 for sub in ['parts', 'p']:
                     candidate = os.path.join(self.shadow_lib_path, sub, normalized)
                     if os.path.exists(candidate):
                         full_path = candidate
                         break
                 else:
                     # One last try: if it has 's\' prefix, maybe it is in parts/s?
                     # (Covered by 'parts' + normalized if normalized is s/...)
                     # If still not found, return empty
                     print(f"Warning: Could not find shadow file: {part_filename}")
                     return []

        connection_points = []
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith('0 !LDCAD SNAP'):
                        continue
                    
                    # We have a SNAP command
                    cmd_type_match = re.match(r'0 !LDCAD (SNAP_[A-Z]+)\s*(.*)', line)
                    if not cmd_type_match:
                        continue
                    
                    cmd_type = cmd_type_match.group(1)
                    args_str = cmd_type_match.group(2)
                    
                    properties = self._parse_properties(args_str)
                    
                    if cmd_type == 'SNAP_INCL':
                        # Recursive inclusion
                        ref_file = properties.get('ref')
                        if ref_file:
                            included_points = self.parse_part(ref_file)
                            # Apply transformations if 'pos'/'ori'/'matrix' are present on the INCL line
                            # NOTE: The shadow library spec says INCL usually just pulls in the definitions.
                            # Often they are used for primitives stud.dat etc.
                            # If the INCL line has transformations, they apply to the imported points.
                            transformed = self._transform_points(included_points, properties)
                            connection_points.extend(transformed)
                    else:
                        # It's a definition (SNAP_CYL, SNAP_FGR, SNAP_GEN)
                        # We need to handle grids here or in normalization
                        points = self._expand_grid(cmd_type, properties)
                        connection_points.extend(points)
                        
        except Exception as e:
            print(f"Error parsing {part_filename}: {e}")
            
        self._cache[part_filename] = connection_points
        return connection_points

    def _parse_properties(self, args_str: str) -> Dict[str, str]:
        """
        Parses string like "[gender=M] [caps=one]" into a dict.
        """
        props = {}
        # Regex to find [key=value] or [key=v1 v2 v3...]
        # Value can contain spaces. e.g. [pos=0 24 0]
        # We assume brackets are balanced and not nested for now.
        matches = re.finditer(r'\[([a-zA-Z0-9_]+)=([^\]]+)\]', args_str)
        for m in matches:
            key = m.group(1)
            val = m.group(2).strip()
            props[key] = val
        return props

    def _expand_grid(self, cmd_type: str, props: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Takes a single SNAP definition and returns a list of points (usually 1, unless grid is used).
        """
        base_point = {
            'type': cmd_type,
            'gender': props.get('gender', 'U'), # U for Unknown/Universal
            'role': props.get('id', 'unknown'), # generic ID if provided
            'properties': props, # Keep raw properties for specialized logic
            'pos': self._parse_vector(props.get('pos', '0 0 0')),
            'ori': self._parse_matrix(props.get('ori', '1 0 0 0 1 0 0 0 1'))
        }
        
        if 'grid' not in props:
            return [base_point]
            
        # Grid syntax: [grid=Type N Steps Start Delta ...] 
        # C N M (Circle/Rect?) or generic?
        # Example from 3003s01.dat: [grid=C 2 C 2 20 20]
        # This implies a 2x2 grid.
        # Let's handle "C N C M SpacingX SpacingY" logic if standard
        # Or "C X_Count C Z_Count Spacing_X Spacing_Z"?
        
        # NOTE: LDCad docs/source would be better, but assuming "C count C count spacing spacing" 
        # based on context (circles/centers?)
        
        grid_tokens = props['grid'].split()
        if len(grid_tokens) >= 6 and grid_tokens[0] == 'C' and grid_tokens[2] == 'C':
            # Rectangular grid centered?
            count_x = int(grid_tokens[1])
            count_z = int(grid_tokens[3])
            spacing_x = float(grid_tokens[4])
            spacing_z = float(grid_tokens[5])
            
            points = []
            
            # center offset
            start_x = -((count_x - 1) * spacing_x) / 2
            start_z = -((count_z - 1) * spacing_z) / 2
            
            for ix in range(count_x):
                for iz in range(count_z):
                    px = start_x + (ix * spacing_x)
                    pz = start_z + (iz * spacing_z)
                    
                    # Create new point copy
                    new_p = base_point.copy()
                    # Apply offset to base pos
                    # Assuming grid is local XZ plane usually?
                    base_pos = new_p['pos']
                    new_p['pos'] = [
                        base_pos[0] + px,
                        base_pos[1],
                        base_pos[2] + pz
                    ]
                    points.append(new_p)
            return points
            
        return [base_point]
        
    def _parse_vector(self, s: str) -> List[float]:
        return [float(x) for x in s.split()]

    def _parse_matrix(self, s: str) -> List[float]:
        # LDraw orientation is 9 floats: R11 R12 R13 R21...
        # LDCad 'ori' prop is usually standard rotation matrix
        return [float(x) for x in s.split()]

    def _transform_points(self, points: List[Dict[str, Any]], props: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Apply transformation (pos/ori) to a list of points.
        Useful for SNAP_INCL.
        """
        # If no transform, return as is
        if 'pos' not in props and 'ori' not in props:
            return points

        offset = self._parse_vector(props.get('pos', '0 0 0'))
        rotation = self._parse_matrix(props.get('ori', '1 0 0 0 1 0 0 0 1'))

        transformed = []
        for p in points:
            new_p = p.copy()
            # Apply rotation to position
            old_pos = p['pos']
            
            # Matrix mult: Rot * old_pos
            rx = rotation[0]*old_pos[0] + rotation[1]*old_pos[1] + rotation[2]*old_pos[2]
            ry = rotation[3]*old_pos[0] + rotation[4]*old_pos[1] + rotation[5]*old_pos[2]
            rz = rotation[6]*old_pos[0] + rotation[7]*old_pos[1] + rotation[8]*old_pos[2]
            
            # Add offset
            new_p['pos'] = [rx + offset[0], ry + offset[1], rz + offset[2]]
            
            # Update orientation (ParentRot * ChildRot)
            # This is simplified; we might need full matrix mult for 'ori'
            # For now, let's assume strict validation mostly looks at position
            # and generic "up vector" alignment.
            # TODO: Full matrix multiplication for orientation
            
            transformed.append(new_p)
            
        return transformed

if __name__ == "__main__":
    # Quick test
    import json
    parser = ShadowParser(r"data\offLibShadow")
    # Test with a known file if it exists
    res = parser.parse_part("parts/3003.dat")
    print(json.dumps(res, indent=2))
