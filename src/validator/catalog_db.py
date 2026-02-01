"""
SQLite-based catalog for LDraw part information.
Stores connection points, bounds, and classification for all parts.
"""

import sqlite3
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple

DB_PATH = Path(__file__).parent / "data" / "catalog.db"

@dataclass
class PartInfo:
    """Information about a single LDraw part."""
    part_id: str
    part_name: str  # Human-readable name from LDraw file
    type: Optional[str]  # First word from part name (e.g., "Brick", "Minifig", "Slope")
    category: Optional[str]  # Raw !CATEGORY metadata or None
    ldraw_org: Optional[str]  # !LDRAW_ORG metadata (e.g., "Part", "Shortcut", "Primitive")
    height: float
    bounds: dict  # {"x": (min, max), "y": (min, max), "z": (min, max)}
    studs: List[Tuple[float, float, float]]
    anti_studs: List[Tuple[float, float, float]]
    technic_holes: List[Tuple[float, float, float]]  # Pin/axle hole positions
    extraction_status: str  # success, partial, failed

    @property
    def name(self) -> str:
        """Compatibility property for old catalog.py 'name' field."""
        return self.part_id


# Common stud primitives in LDraw (Moved from catalog.py)
STUD_PRIMITIVES = {
    "stud.dat", "stud2.dat", "stud3.dat", "stud4.dat", "stud6.dat",
    "stud10.dat", "stud12.dat", "stud15.dat", "studp01.dat", "studel.dat"
}


def get_part(part_id: str) -> Optional[PartInfo]:
    """
    Helper function to load a part from the database without manual connection management.
    Compatibility replacement for validator.catalog.get_part.
    """
    conn = init_db()
    try:
        return load_part(conn, part_id)
    finally:
        conn.close()



def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Initialize the SQLite database with schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    
    # Enable Write-Ahead Logging for better concurrency
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass  # Best effort
    
    # Create base table without image fields first
    conn.execute("""
        CREATE TABLE IF NOT EXISTS parts (
            part_id TEXT PRIMARY KEY,
            category TEXT,
            height REAL,
            bounds_json TEXT,
            studs_json TEXT,
            anti_studs_json TEXT,
            technic_holes_json TEXT,
            extraction_status TEXT DEFAULT 'pending'
        )
    """)
    
    # Migrate to add image fields if needed
    try:
        conn.execute("ALTER TABLE parts ADD COLUMN has_image BOOLEAN DEFAULT 0")
        conn.execute("ALTER TABLE parts ADD COLUMN image_path TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Columns already exist
        pass
    
    # Migrate to add part_name field if needed
    try:
        conn.execute("ALTER TABLE parts ADD COLUMN part_name TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Migrate to add type field if needed
    try:
        conn.execute("ALTER TABLE parts ADD COLUMN type TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Migrate to add ldraw_org field if needed
    try:
        conn.execute("ALTER TABLE parts ADD COLUMN ldraw_org TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Create indices
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_category ON parts(category)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_type ON parts(type)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ldraw_org ON parts(ldraw_org)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_status ON parts(extraction_status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_has_image ON parts(has_image)
    """)
    conn.commit()
    return conn


def migrate_add_image_fields(conn: sqlite3.Connection) -> None:
    """Add image tracking fields if they don't exist. (No longer needed, kept for compatibility)"""
    pass


def save_part(conn: sqlite3.Connection, part: PartInfo) -> None:
    """Save a part to the database, preserving existing image data."""
    # First, check if part exists and has image data
    cursor = conn.execute(
        "SELECT has_image, image_path FROM parts WHERE part_id = ?", 
        (part.part_id,)
    )
    existing = cursor.fetchone()
    
    if existing:
        # Preserve existing image data
        has_image, image_path = existing
    else:
        # New part, no image data
        has_image, image_path = 0, None
    
    conn.execute("""
        INSERT OR REPLACE INTO parts 
        (part_id, part_name, type, category, ldraw_org, height, bounds_json, studs_json, anti_studs_json, technic_holes_json, extraction_status, has_image, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        part.part_id,
        part.part_name,
        part.type,
        part.category,
        part.ldraw_org,
        part.height,
        json.dumps(part.bounds),
        json.dumps(part.studs),
        json.dumps(part.anti_studs),
        json.dumps(part.technic_holes),
        part.extraction_status,
        has_image,
        image_path
    ))


def load_part(conn: sqlite3.Connection, part_id: str) -> Optional[PartInfo]:
    """Load a part from the database."""
    cursor = conn.execute(
        "SELECT part_id, part_name, type, category, ldraw_org, height, bounds_json, studs_json, anti_studs_json, technic_holes_json, extraction_status FROM parts WHERE part_id = ?", (part_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    
    return PartInfo(
        part_id=row[0],
        part_name=row[1] or row[0],  # Fall back to ID if no name
        type=row[2],
        category=row[3],
        ldraw_org=row[4],
        height=row[5],
        bounds=json.loads(row[6]) if row[6] else {},
        studs=json.loads(row[7]) if row[7] else [],
        anti_studs=json.loads(row[8]) if row[8] else [],
        technic_holes=json.loads(row[9]) if row[9] else [],
        extraction_status=row[10]
    )


def get_stats(conn: sqlite3.Connection) -> dict:
    """Get catalog statistics."""
    cursor = conn.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN extraction_status = 'success' THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN extraction_status = 'partial' THEN 1 ELSE 0 END) as partial,
            SUM(CASE WHEN extraction_status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM parts
    """)
    row = cursor.fetchone()
    return {
        "total": row[0],
        "success": row[1] or 0,
        "partial": row[2] or 0,
        "failed": row[3] or 0
    }


def get_parts_by_category(conn: sqlite3.Connection, category: str) -> List[str]:
    """Get all part IDs of a given category."""
    cursor = conn.execute(
        "SELECT part_id FROM parts WHERE category = ?", (category,)
    )
    return [row[0] for row in cursor.fetchall()]
