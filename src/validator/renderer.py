import subprocess
import os
import tempfile
from pathlib import Path
from typing import Optional
from validator.scene_graph import SceneGraph
from validator.parser import Placement

def render_scene(scene_graph: SceneGraph, output_path: str, width: int = 800, height: int = 600) -> bool:
    """
    Render the scene graph to an image file using LDView.
    
    Args:
        scene_graph: The scene layout to render.
        output_path: Path to write the output image (e.g. 'out.png').
        width: Image width.
        height: Image height.
        
    Returns:
        True if successful, False otherwise.
    """
    
    # 1. Export SceneGraph to a temporary LDraw file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ldr', delete=False) as tmp_file:
        tmp_path = tmp_file.name
        
        # Write header
        tmp_file.write("0 MOC Render\n")
        
        # Write placements
        for placement in scene_graph.placements:
            # LDraw line type 1: 1 <color> x y z a b c d e f g h i <part>
            # We need to construct the rotation matrix string
            # Our placement.rotation is (r00, r01, r02, r10, r11, r12, r20, r21, r22)
            # LDraw format expects: a b c d e f g h i  (column major? or row major?)
            # LDraw spec:
            # x y z = position
            # a b c = top row of rotation matrix
            # d e f = middle row
            # g h i = bottom row
            
            # Checks existing loader code or parser code to verify matching convention.
            # Assuming our rotation tuple is row-major.
            
            r = placement.rotation
            pos = placement.position
            part_id = placement.part_id.replace('/', '\\') # Ensure windows paths for parts
            
            # Color 16 (Main color) if not specified? 
            # Our Placement struct doesn't have color yet?
            # Creating mocks, we didn't add color. Defaults to 7 (Light Gray) or 4 (Red).
            color = 4 
            
            line = f"1 {color} {pos[0]} {pos[1]} {pos[2]} {r[0]} {r[1]} {r[2]} {r[3]} {r[4]} {r[5]} {r[6]} {r[7]} {r[8]} {part_id}.dat\n"
            tmp_file.write(line)
            
    # 2. Run LDView
    # Assuming LDView is in PATH or known location.
    # Try standard locations if not in PATH.
    ldview_cmd = "LDView"
    
    possible_paths = [
        r"C:\Program Files\LDView\LDView.exe",
        r"C:\Program Files (x86)\LDView\LDView.exe",
        r"C:\LDView\LDView.exe"
    ]
    
    # Check if 'LDView' is in path? 
    # shutil.which("LDView")?
    import shutil
    if shutil.which("LDView"):
        ldview_cmd = "LDView"
    else:
        for p in possible_paths:
            if os.path.exists(p):
                ldview_cmd = p
                break
    
    # Construct args
    # LDView-4.5.exe input.ldr -SaveWidth=800 -SaveHeight=600 -SaveSnapshot=output.png -DefaultLatLong=45,45
    
    args = [
        ldview_cmd,
        tmp_path,
        f"-SaveWidth={width}",
        f"-SaveHeight={height}",
        f"-SaveSnapshot={output_path}",
        "-DefaultLatLong=30,45", # Camera angle
        "-ProcessLDConfig=0" # Don't try to load LDConfig if it causes issues? Or do.
    ]
    
    try:
        # Capture output for debugging
        result = subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        success = True
    except subprocess.CalledProcessError as e:
        print(f"LDView failed: {e.stderr}")
        success = False
    except FileNotFoundError:
        print("LDView executable not found.")
        success = False
    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
            
    return success
