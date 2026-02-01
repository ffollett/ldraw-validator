import subprocess
import os
import tempfile
from pathlib import Path
from typing import Optional
from validator.scene_graph import SceneGraph
from validator.parser import Placement

def render_scene(scene_graph: SceneGraph, output_path: str, width: int = 256, height: int = 256, silent_errors: bool = False) -> bool:
    """
    Render the scene graph to an image file using LDView.
    
    Args:
        scene_graph: The scene layout to render.
        output_path: Path to write the output image (e.g. 'out.png').
        width: Image width (default 256).
        height: Image height (default 256).
        silent_errors: If True, suppress error messages (for batch mode).
        
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
            r = placement.rotation
            pos = placement.position
            part_id = placement.part_id.replace('/', '\\')
            color = placement.color
            
            line = f"1 {color} {pos[0]} {pos[1]} {pos[2]} {r[0]} {r[1]} {r[2]} {r[3]} {r[4]} {r[5]} {r[6]} {r[7]} {r[8]} {part_id}.dat\n"
            tmp_file.write(line)
            
    # 2. Find LDView
    ldview_cmd = None
    
    possible_paths = [
        r"C:\Program Files\LDView\LDView64.exe",
        r"C:\Program Files\LDView\LDView.exe",
        r"C:\Program Files (x86)\LDView\LDView.exe",
        r"C:\LDView\LDView.exe"
    ]
    
    import shutil
    if shutil.which("LDView64"):
        ldview_cmd = "LDView64"
    elif shutil.which("LDView"):
        ldview_cmd = "LDView"
    else:
        for p in possible_paths:
            if os.path.exists(p):
                ldview_cmd = p
                break
    
    if not ldview_cmd:
        if not silent_errors:
            print("LDView executable not found.")
        return False
    
    # 3. Build command args
    from validator.config import LDRAW_PATH
    
    args = [
        ldview_cmd,
        tmp_path,
        f"-LDrawDir={LDRAW_PATH}",
        f"-SaveWidth={width}",
        f"-SaveHeight={height}",
        f"-SaveSnapshot={output_path}",
        "-DefaultLatLong=30,45",
        "-BackgroundColor=0xFFFFFF",
        "-DefaultColor=0x7F7F7F",
        "-LDConfig=1",
        "-Lighting=1",
        "-UseQualityLighting=1",
        "-SubduedLighting=0",
        "-SaveAlpha=0",
        "-SaveZoomToFit=1",
        "-EdgeLines=1",
        "-BlackHighlights=0",
        # Memory optimization
        "-MemoryUsage=2",
        "-MaxAnisotropy=1",
    ]
    
    try:
        result = subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        success = True
    except subprocess.CalledProcessError as e:
        if not silent_errors:
            print(f"LDView failed: {e.stderr}")
        success = False
    except FileNotFoundError:
        if not silent_errors:
            print("LDView executable not found.")
        success = False
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
            
    return success

