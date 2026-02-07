"""
Restore image metadata from rendered_images directory to catalog database.
Run this after rebuilding the catalog to restore image links.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validator.catalog_db import init_db

def main():
    conn = init_db()
    
    # Find all rendered images
    image_dir = Path(__file__).parent.parent / "data" / "part_images"
    
    if not image_dir.exists():
        print(f"No part images directory found at {image_dir}")
        print("Images have not been downloaded yet.")
        return
    
    images = list(image_dir.glob("*.png"))
    print(f"Found {len(images)} part images in {image_dir}")
    
    if not images:
        print("No images to restore.")
        return
    
    # Update database
    updated = 0
    not_found = 0
    
    for img in images:
        part_id = img.stem
        rel_path = f"data/part_images/{part_id}.png"
        
        # Check if part exists
        cursor = conn.execute("SELECT part_id FROM parts WHERE part_id = ?", (part_id,))
        if cursor.fetchone():
            conn.execute(
                "UPDATE parts SET has_image = 1, image_path = ? WHERE part_id = ?",
                (rel_path, part_id)
            )
            updated += 1
        else:
            not_found += 1
    
    conn.commit()
    conn.close()
    
    print(f"Updated {updated} parts with image metadata")
    if not_found > 0:
        print(f"Warning: {not_found} images found for parts not in catalog")
    print("Done!")

if __name__ == "__main__":
    main()
