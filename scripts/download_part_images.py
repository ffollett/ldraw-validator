"""
Download images for all parts in the catalog from the LDraw library.
"""

import argparse
import requests
from bs4 import BeautifulSoup
import sqlite3
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validator.catalog_db import DB_PATH

# Where to store downloaded images
IMAGE_DIR = Path(__file__).parent.parent / "data" / "part_images"


def get_image_url(part_id):
    """
    Fetch the image URL for a part from the LDraw library using search.
    This is more robust than guessing URLs because the library uses internal IDs.
    
    Args:
        part_id: The part ID (e.g., '3001')
    
    Returns:
        Image URL string or None if not found
    """
    # Use the list search which returns exact matches in a table
    url = "https://library.ldraw.org/parts/list"
    params = {'tableSearch': part_id}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  ✗ Error searching for {part_id}: {e}")
        return None
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all rows/entries
    # The structure is a bit complex (Livewire), but generally images and text are in the same container.
    # We look for links that contain the part filename
    
    target_filename = f"parts/{part_id}.dat".lower()
    
    # Find all links to parts
    for link in soup.find_all('a', href=True):
        if '/parts/' in link['href']:
            # Check if this link corresponds to our part
            # The text inside usually contains the filename "parts/3001.dat"
            # It might be in a child div
            text = link.get_text().strip().lower()
            
            # Use exact match on filename to avoid partial matches (e.g. 10154 matching 10154s01)
            # We look for the filename appearing as a distinct word/token
            if target_filename in text:
                 # Found the right entry! Now find the image associated with it.
                 # Usually the image is in a sibling div or parent container.
                 # Let's verify the container structure.
                 # In the observed HTML, the image is in a sibling column to the text column
                 # The safest way is to look at the parent 'tr' or 'div' row.
                 
                 # Traverse up to finding the row container
                 container = link.find_parent('div', class_='fi-ta-record')
                 if not container:
                     container = link.find_parent('tr') # Fallback if table structure
                 
                 if container:
                     img = container.find('img')
                     if img and img.get('src'):
                         thumb_url = img['src']
                         # Convert thumb to high-res feed image
                         # .../conversions/10154-thumb.png -> .../conversions/10154-feed-image.png
                         if '-thumb' in thumb_url:
                             return thumb_url.replace('-thumb', '-feed-image')
                         return thumb_url
                         
    # If no exact match found in list, try fuzzy check or return None
    return None


def download_image(part_id, image_url, output_dir):
    """
    Download an image from a URL.
    
    Args:
        part_id: The part ID
        image_url: URL to download from
        output_dir: Directory to save to
    
    Returns:
        Path to saved file or None if failed
    """
    try:
        response = requests.get(image_url, timeout=15, stream=True)
        response.raise_for_status()
        
        # Determine file extension from URL
        ext = '.png'  # Default
        if '.' in image_url:
            ext = '.' + image_url.split('.')[-1].split('?')[0]
        
        # Save to file
        output_path = output_dir / f"{part_id}{ext}"
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return output_path
    except requests.RequestException as e:
        print(f"  ✗ Error downloading image for {part_id}: {e}")
        return None


def process_part(part_id, output_dir, force=False):
    """
    Process a single part: fetch image URL and download.
    
    Returns:
        tuple: (part_id, success, image_path)
    """
    # Check if image already exists
    existing_image = None
    for ext in ['.png', '.jpg', '.jpeg', '.gif']:
        potential_path = output_dir / f"{part_id}{ext}"
        if potential_path.exists():
            existing_image = potential_path
            break
    
    if existing_image and not force:
        return (part_id, True, str(existing_image.relative_to(output_dir.parent.parent)))
    
    # Fetch image URL
    image_url = get_image_url(part_id)
    if not image_url:
        return (part_id, False, None)
    
    # Download image
    image_path = download_image(part_id, image_url, output_dir)
    if not image_path:
        return (part_id, False, None)
    
    # Return relative path for database storage
    rel_path = str(image_path.relative_to(output_dir.parent.parent))
    return (part_id, True, rel_path)


def update_database(db_path, part_id, has_image, image_path):
    """Update the database with image information."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE parts SET has_image = ?, image_path = ? WHERE part_id = ?",
            (1 if has_image else 0, image_path, part_id)
        )
        conn.commit()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Download part images from LDraw library")
    parser.add_argument('--force', action='store_true', help='Re-download even if image exists')
    parser.add_argument('--workers', type=int, default=5, help='Number of parallel workers (default: 5)')
    parser.add_argument('--limit', type=int, help='Limit number of parts to process (for testing)')
    parser.add_argument('--category', help='Only process parts in this category')
    parser.add_argument('--missing-only', action='store_true', help='Only download for parts without images')
    parser.add_argument('--resume-from', help='Resume processing from this part ID (inclusive)')
    
    args = parser.parse_args()
    
    # Create output directory
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Connect to database and get all parts
    conn = sqlite3.connect(DB_PATH)
    
    # Build query
    query = "SELECT part_id, has_image, image_path FROM parts"
    params = []
    
    if args.category:
        query += " WHERE category = ?"
        params.append(args.category)
    
    if args.missing_only:
        if args.category:
            query += " AND (has_image = 0 OR has_image IS NULL)"
        else:
            query += " WHERE (has_image = 0 OR has_image IS NULL)"
            
    query += " ORDER BY part_id"
    
    cursor = conn.execute(query, params)
    parts = cursor.fetchall()
    conn.close()
    
    if args.resume_from:
        parts = [p for p in parts if p[0] >= args.resume_from]
        print(f"Resuming from {args.resume_from} (inclusive)")
    
    if args.limit:
        parts = parts[:args.limit]
    
    total = len(parts)
    print(f"Processing {total} parts...")
    print(f"Workers: {args.workers}")
    print(f"Output directory: {IMAGE_DIR}")
    print()
    
    # Process parts in parallel
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all tasks
        future_to_part = {
            executor.submit(process_part, part_id, IMAGE_DIR, args.force): part_id 
            for part_id, has_image, image_path in parts
        }
        
        # Process results as they complete
        for i, future in enumerate(as_completed(future_to_part), 1):
            part_id = future_to_part[future]
            
            try:
                result_part_id, success, image_path = future.result()
                
                if success:
                    # Update database
                    update_database(DB_PATH, result_part_id, True, image_path)
                    
                    # Check if it was already there
                    original_part = next((p for p in parts if p[0] == result_part_id), None)
                    if original_part and original_part[1] and not args.force:
                        print(f"[{i}/{total}] ✓ {result_part_id} (already had image)")
                        skipped_count += 1
                    else:
                        print(f"[{i}/{total}] ✓ {result_part_id} → {image_path}")
                        success_count += 1
                else:
                    update_database(DB_PATH, result_part_id, False, None)
                    print(f"[{i}/{total}] ✗ {result_part_id} (failed)")
                    failed_count += 1
                    
            except Exception as e:
                print(f"[{i}/{total}] ✗ {part_id} (exception: {e})")
                failed_count += 1
            
            # Small delay to be nice to the server
            if i % 10 == 0:
                time.sleep(0.5)
    
    # Summary
    print()
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total parts processed: {total}")
    print(f"Successfully downloaded: {success_count}")
    print(f"Already had images: {skipped_count}")
    print(f"Failed: {failed_count}")
    print(f"Images saved to: {IMAGE_DIR}")


if __name__ == "__main__":
    main()
