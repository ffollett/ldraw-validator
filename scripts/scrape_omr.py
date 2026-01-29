import argparse
import requests
from bs4 import BeautifulSoup
import os
import sys

BASE_URL = "https://library.ldraw.org"

def fetch_set_list():
    """Calculates the total number of sets and fetches them."""
    # The /omr/sets/ page might be paginated or just a list. 
    # Let's inspect /omr/sets/ first. 
    # For now, we will implement a basic fetch that gets the main page.
    # The user mentioned /omr/sets/ should enumerate all sets.
    # We might need to handle pagination if it exists, but let's start with page 1.
    
    # Actually, let's try to visit the URL or assume it works.
    # User said: "/omr/sets/ should enumerate all sets"
    # We'll just fetch that page.
    url = f"{BASE_URL}/omr/sets"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching set list: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # We need to find the links to sets.
    # Expected format: /omr/sets/1383
    # We'll look for 'a' tags with href containing '/omr/sets/'
    sets = []
    
    # This is a bit speculative without seeing the lists page HTML. 
    # But often it's a table or list of links.
    for link in soup.find_all('a', href=True):
        href = link['href']
        # Check if it looks like a set link
        if '/omr/sets/' in href:
             if href.startswith('http'):
                 full_url = href
             else:
                 full_url = BASE_URL + href if href.startswith('/') else f"{BASE_URL}/{href}"
             
             # Extract ID
             # valid formats: .../sets/123 or .../sets/123/something?
             # Let's assume the ID is the segment after 'sets'
             parts = full_url.split('/')
             try:
                 # valid structure .../omr/sets/123
                 if 'sets' in parts:
                     idx = parts.index('sets')
                     if idx + 1 < len(parts):
                         potential_id = parts[idx+1]
                         # Strip queries or fragments if any
                         potential_id = potential_id.split('?')[0].split('#')[0]
                         if potential_id.isdigit():
                             sets.append({'id': potential_id, 'url': full_url})
             except Exception as e:
                 continue
                 
    # Deduplicate
    unique_sets = {s['id']: s for s in sets}.values()
    return list(unique_sets)

def download_set(set_id, output_dir="downloads"):
    """Downloads models for a specific set."""
    url = f"{BASE_URL}/omr/sets/{set_id}"
    print(f"Fetching set page: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching set page {set_id}: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # The user provided snippet has models in blocks.
    # We need to find download links. 
    # Snippet: <a ... href="https://library.ldraw.org/library/omr/10281-1.mpd">Download</a>
    
    download_links = []
    
    # Strategy 1: Find all 'a' tags with text "Download" and href ending in .mpd, .ldr
    for link in soup.find_all('a', href=True):
        if link.text.strip() == "Download":
            href = link['href']
            if href.endswith('.mpd') or href.endswith('.ldr') or href.endswith('.dat'):
                download_links.append(href)
    
    if not download_links:
        print(f"No download links found for set {set_id}.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for link in download_links:
        filename = link.split('/')[-1]
        output_path = os.path.join(output_dir, filename)
        
        print(f"Downloading {filename} from {link}...")
        try:
            r = requests.get(link, stream=True)
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Saved to {output_path}")
        except requests.RequestException as e:
            print(f"Failed to download {link}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Scrape LDraw OMR sets.")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # List command
    list_parser = subparsers.add_parser('list', help='List all available sets')

    # Download command
    download_parser = subparsers.add_parser('download', help='Download models for a set')
    download_parser.add_argument('--set', required=True, help='Set ID to download (e.g., 1383)')
    download_parser.add_argument('--output', default='downloads', help='Output directory')

    args = parser.parse_args()

    if args.command == 'list':
        sets = fetch_set_list()
        print(f"Found {len(sets)} sets:")
        for s in sets:
            print(f"ID: {s['id']} - URL: {s['url']}")
            
    elif args.command == 'download':
        download_set(args.set, args.output)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
