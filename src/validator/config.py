from pathlib import Path
import os

# Default to C:\LDraw\ldraw if not specified
LDRAW_PATH = Path(os.environ.get("LDRAW_PATH", r"C:\LDraw\ldraw"))

def get_parts_dir() -> Path:
    return LDRAW_PATH / "parts"

def get_p_dir() -> Path:
    return LDRAW_PATH / "p"
