#!/usr/bin/env python
"""
Scan LDraw parts to find all !CATEGORY metadata.
"""
from pathlib import Path
from collections import Counter
import re

parts_dir = Path(r"C:\LDraw\ldraw\parts")
categories = Counter()
examples = {}

print("Scanning LDraw parts for !CATEGORY metadata...")

for i, part_file in enumerate(parts_dir.glob("*.dat")):
    if i % 1000 == 0:
        print(f"  Scanned {i} parts...")
    
    try:
        with open(part_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if '!CATEGORY' in line:
                    # Extract category name
                    match = re.search(r'!CATEGORY\s+(.+)', line)
                    if match:
                        category = match.group(1).strip()
                        categories[category] += 1
                        if category not in examples:
                            examples[category] = part_file.stem
                    break
                # Stop after header section
                if line.strip() and not line.startswith('0'):
                    break
    except Exception as e:
        pass

print(f"\nFound {len(categories)} unique categories in {sum(categories.values())} parts\n")
print("=" * 60)
print("LDRAW CATEGORIES (sorted by frequency)")
print("=" * 60)

for category, count in categories.most_common():
    example = examples.get(category, "")
    print(f"{count:5d}  {category:40s}  (e.g., {example})")

print("\n" + "=" * 60)
print(f"Total parts with !CATEGORY: {sum(categories.values())}")
print(f"Total parts scanned: {len(list(parts_dir.glob('*.dat')))}")
print("=" * 60)
