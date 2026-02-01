"""
Flask web app for browsing the LDraw part catalog.
"""

from flask import Flask, render_template, jsonify, send_file, request, g, Response
from pathlib import Path
import sys
import threading
import time
import uuid
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validator.catalog_db import init_db, load_part, get_stats

app = Flask(__name__)

# Batch job management
batch_jobs = {}  # job_id -> job_info
batch_lock = threading.Lock()


def get_db():
    """Get database connection for current request (thread-safe)."""
    if 'db' not in g:
        g.db = init_db()
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


@app.route('/')
def index():
    """Serve the main catalog viewer page."""
    return render_template('index.html', active_page='catalog')


@app.route('/stats')
def stats_page():
    """Serve the stats dashboard page."""
    return render_template('stats.html', active_page='stats')


@app.route('/batch')
def batch_page():
    """Serve the batch render page."""
    return render_template('batch.html', active_page='batch')


# LDraw library file routes for 3D viewer
def get_ldraw_file(filename):
    """Centralized helper to find LDraw files in various directories."""
    from validator.config import LDRAW_PATH
    
    # Strip any redundant 'parts/', 'p/', or 'models/' prefixes from the filename
    # Some loaders (like Three.js LDrawLoader) might concatenate these
    clean_name = filename
    for prefix in ['parts/', 'p/', 'models/']:
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix):]
            
    # Try multiple search locations
    search_dirs = ['parts', 'p', 'models', ''] # '' for root
    for subdir in search_dirs:
        if subdir:
            file_path = LDRAW_PATH / subdir / clean_name
        else:
            file_path = LDRAW_PATH / clean_name
            
        if file_path.exists():
            return file_path
            
    # Also try with the original name just in case
    for subdir in search_dirs:
        if subdir:
            file_path = LDRAW_PATH / subdir / filename
        else:
            file_path = LDRAW_PATH / filename
        if file_path.exists():
            return file_path
            
    return None

@app.route('/parts/<path:filename>')
def serve_ldraw_parts(filename):
    """Serve LDraw parts files for 3D viewer."""
    file_path = get_ldraw_file(filename)
    if file_path:
        return send_file(file_path, mimetype='text/plain')
    return "Not found", 404

@app.route('/p/<path:filename>')
def serve_ldraw_primitives(filename):
    """Serve LDraw primitive files for 3D viewer."""
    file_path = get_ldraw_file(filename)
    if file_path:
        return send_file(file_path, mimetype='text/plain')
    return "Not found", 404

@app.route('/models/<path:filename>')
def serve_ldraw_models(filename):
    """Serve LDraw model files for 3D viewer."""
    file_path = get_ldraw_file(filename)
    if file_path:
        return send_file(file_path, mimetype='text/plain')
    return "Not found", 404

@app.route('/<path:filename>')
def serve_ldraw_root(filename):
    """Serve LDraw files from root path."""
    # Allow .dat and .ldr files
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    if ext not in ['dat', 'ldr']:
        return "Not found", 404
        
    # Handle common material file paths explicitly
    from validator.config import LDRAW_PATH
    if filename.lower() in ['ldconfig.ldr', 'colors/ldcfg.ldr']:
        targets = [LDRAW_PATH / "LDConfig.ldr", LDRAW_PATH / "colors" / "ldcfg.ldr"]
        for target in targets:
            if target.exists():
                return send_file(target, mimetype='text/plain')

    file_path = get_ldraw_file(filename)
    if file_path:
        return send_file(file_path, mimetype='text/plain')
            
    return "Not found", 404


@app.route('/api/batch/start', methods=['POST'])
def api_batch_start():
    """Start a batch rendering job in the background."""
    from validator.scene_graph import SceneGraph
    from validator.parser import Placement
    from validator.renderer import render_scene
    
    data = request.get_json()
    categories = data.get('categories', '')
    images = data.get('images', '')
    extractions = data.get('extractions', '')
    limit = int(data.get('limit', 100))
    
    # Get matching parts
    conn = init_db()
    where_clauses = []
    params = []
    
    types = data.get('types', '')
    
    # Handle categories (comma-separated)
    if categories:
        category_list = [c.strip() for c in categories.split(',')]
        if 'all' not in category_list:
            placeholders = ','.join(['?' for _ in category_list])
            where_clauses.append(f"category IN ({placeholders})")
            params.extend(category_list)
            
    # Handle types (comma-separated)
    if types:
        type_list = [t.strip() for t in types.split(',')]
        if 'all' not in type_list:
            standard_types = ['Brick', 'Plate', 'Tile', 'Slope', 'Technic', 'Minifig', 'Vehicle', 'Building', 'Electric', 'Sticker', 'Specialized', 'Obsolete']
            
            has_other = 'Other' in type_list
            selected_standard = [t for t in type_list if t in standard_types]
            
            type_conditions = []
            if selected_standard:
                placeholders = ','.join(['?' for _ in selected_standard])
                type_conditions.append(f"type IN ({placeholders})")
                params.extend(selected_standard)
                
            if has_other:
                placeholders = ','.join(['?' for _ in standard_types])
                type_conditions.append(f"type NOT IN ({placeholders}) OR type IS NULL")
                params.extend(standard_types)
                
            if type_conditions:
                where_clauses.append(f"({' OR '.join(type_conditions)})")
    
    # Handle ldraw_org (comma-separated)
    ldraw_orgs = data.get('ldraw_orgs', '')
    if ldraw_orgs:
        org_list = [o.strip() for o in ldraw_orgs.split(',')]
        if 'all' not in org_list:
            where_clauses.append(f"ldraw_org IN ({placeholders})")
            params.extend(org_list)
    
    # Handle images (comma-separated: yes, no)
    if images:
        image_list = [i.strip() for i in images.split(',')]
        if 'all' not in image_list:
            image_conditions = []
            if 'yes' in image_list:
                image_conditions.append("has_image = 1")
            if 'no' in image_list:
                image_conditions.append("has_image = 0")
            if image_conditions:
                where_clauses.append(f"({' OR '.join(image_conditions)})")
    
    # Handle extractions (comma-separated)
    if extractions:
        extraction_list = [e.strip() for e in extractions.split(',')]
        if 'all' not in extraction_list:
            placeholders = ','.join(['?' for _ in extraction_list])
            where_clauses.append(f"extraction_status IN ({placeholders})")
            params.extend(extraction_list)
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    cursor = conn.execute(f"""
        SELECT part_id FROM parts
        WHERE {where_sql}
        LIMIT ?
    """, params + [limit])
    part_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not part_ids:
        return jsonify({"error": "No parts found matching filters"}), 400
    
    # Create job
    job_id = str(uuid.uuid4())
    job_info = {
        "id": job_id,
        "status": "running",
        "total": len(part_ids),
        "completed": 0,
        "success": 0,
        "failed": 0,
        "current": None,
        "log": [],
        "started": datetime.now().isoformat(),
        "finished": None,
        "filters": f"categories:{categories}, images:{images}, extractions:{extractions}",
        "stopped": False
    }
    
    with batch_lock:
        batch_jobs[job_id] = job_info
    
    # Start rendering thread
    def render_batch():
        # Output to data/rendered_images instead of web/static/rendered
        project_root = Path(__file__).parent.parent
        output_dir = project_root / "data" / "rendered_images"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, part_id in enumerate(part_ids):
            if job_info["stopped"]:
                job_info["log"].append(f"--- STOPPED BY USER ---")
                break
            
            job_info["current"] = part_id
            job_info["completed"] = i + 1
            
            try:
                sg = SceneGraph()
                sg.add_placement(Placement(
                    part_id=part_id,
                    color=16,
                    position=(0.0, 0.0, 0.0),
                    rotation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
                ))
                
                output_path = output_dir / f"{part_id}.png"
                success = render_scene(sg, str(output_path), silent_errors=True)
                
                if success and output_path.exists():
                    # Update database with relative path from project root
                    conn = init_db()
                    rel_path = f"data/rendered_images/{part_id}.png"
                    conn.execute(
                        "UPDATE parts SET has_image = 1, image_path = ? WHERE part_id = ?",
                        (rel_path, part_id)
                    )
                    conn.commit()
                    conn.close()
                    
                    job_info["success"] += 1
                    job_info["log"].append(f"✓ {part_id}")
                else:
                    job_info["failed"] += 1
                    job_info["log"].append(f"✗ {part_id}: render failed")
            except Exception as e:
                job_info["failed"] += 1
                job_info["log"].append(f"✗ {part_id}: {str(e)}")
        
        job_info["status"] = "completed"
        job_info["finished"] = datetime.now().isoformat()
        job_info["log"].append(f"--- COMPLETE: {job_info['success']}/{job_info['total']} rendered ---")
    
    thread = threading.Thread(target=render_batch, daemon=True)
    thread.start()
    
    return jsonify({"job_id": job_id, "total": len(part_ids)})


@app.route('/api/batch/status/<job_id>')
def api_batch_status(job_id):
    """Stream batch job progress via Server-Sent Events."""
    def generate():
        last_log_index = 0
        
        while True:
            with batch_lock:
                job = batch_jobs.get(job_id)
            
            if not job:
                yield f"data: {{\"error\": \"Job not found\"}}\n\n"
                break
            
            # Send progress update
            update = {
                "status": job["status"],
                "completed": job["completed"],
                "total": job["total"],
                "success": job["success"],
                "failed": job["failed"],
                "current": job["current"],
                "new_log": job["log"][last_log_index:]
            }
            last_log_index = len(job["log"])
            
            import json
            yield f"data: {json.dumps(update)}\n\n"
            
            if job["status"] == "completed":
                break
            
            time.sleep(0.5)
    
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/batch/jobs')
def api_batch_jobs():
    """Get list of all batch jobs."""
    with batch_lock:
        jobs_list = list(batch_jobs.values())
    
    # Sort by start time, newest first
    jobs_list.sort(key=lambda j: j["started"], reverse=True)
    
    # Limit to last 50 jobs
    return jsonify({"jobs": jobs_list[:50]})


@app.route('/api/batch/stop/<job_id>', methods=['POST'])
def api_batch_stop(job_id):
    """Stop a running batch job."""
    with batch_lock:
        job = batch_jobs.get(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    if job["status"] == "running":
        job["stopped"] = True
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Job not running"}), 400


@app.route('/api/schema')
def api_schema():
    """Get database schema dynamically."""
    conn = get_db()
    
    # Get table schema using PRAGMA
    cursor = conn.execute("PRAGMA table_info(parts)")
    columns = cursor.fetchall()
    
    # Field descriptions (can be moved to config later)
    descriptions = {
        "part_id": "Primary key - LDraw part identifier (e.g., '3001.dat')",
        "part_name": "Full description from the first line of the LDraw file",
        "type": "Primary part classification (e.g., 'Brick', 'Plate', 'Slope') extracted as the first word of the name",
        "category": "Raw !CATEGORY metadata from LDraw file (NULL if not specified)",
        "ldraw_org": "Official LDraw organization type (e.g., 'Part', 'Shortcut', 'Primitive')",
        "height": "Part height in LDraw units",
        "bounds_json": "Bounding box: {\"x\": [min, max], \"y\": [min, max], \"z\": [min, max]}",
        "studs_json": "Array of stud positions: [[x, y, z], ...]",
        "anti_studs_json": "Array of anti-stud (hollow) positions: [[x, y, z], ...]",
        "technic_holes_json": "Array of pin/axle hole positions: [[x, y, z], ...]",
        "extraction_status": "Status: success, partial, failed, pending",
        "has_image": "Whether a rendered image exists (0 or 1)",
        "image_path": "Absolute path to rendered PNG image"
    }
    
    schema = []
    for col in columns:
        # col = (cid, name, type, notnull, dflt_value, pk)
        schema.append({
            "name": col[1],
            "type": col[2],
            "description": descriptions.get(col[1], ""),
            "is_primary_key": bool(col[5])
        })
    
    return jsonify({"schema": schema})


@app.route('/api/distributions')
def api_distributions():
    """Get value distributions for all fields."""
    import json
    conn = get_db()
    
    distributions = {}
    
    # Categorical fields - pie chart data
    # Category distribution
    cursor = conn.execute("SELECT category, COUNT(*) FROM parts GROUP BY category")
    distributions["category"] = {
        "type": "categorical",
        "values": [{"label": row[0], "count": row[1]} for row in cursor.fetchall()]
    }
    
    # Extraction status distribution
    cursor = conn.execute("SELECT extraction_status, COUNT(*) FROM parts GROUP BY extraction_status")
    distributions["extraction_status"] = {
        "type": "categorical",
        "values": [{"label": row[0], "count": row[1]} for row in cursor.fetchall()]
    }
    
    # Has image distribution
    cursor = conn.execute("SELECT has_image, COUNT(*) FROM parts GROUP BY has_image")
    distributions["has_image"] = {
        "type": "categorical",
        "values": [{"label": "Yes" if row[0] else "No", "count": row[1]} for row in cursor.fetchall()]
    }
    
    # Type distribution (Top 50)
    cursor = conn.execute("SELECT type, COUNT(*) as cnt FROM parts GROUP BY type ORDER BY cnt DESC LIMIT 50")
    distributions["type"] = {
        "type": "categorical",
        "values": [{"label": row[0] or "Unknown", "count": row[1]} for row in cursor.fetchall()]
    }
    
    # Category distribution (Top 50)
    cursor = conn.execute("SELECT category, COUNT(*) as cnt FROM parts GROUP BY category ORDER BY cnt DESC LIMIT 50")
    distributions["category"] = {
        "type": "categorical",
        "values": [{"label": row[0] or "(No Category)", "count": row[1]} for row in cursor.fetchall()]
    }
    cursor = conn.execute("SELECT ldraw_org, COUNT(*) FROM parts GROUP BY ldraw_org")
    distributions["ldraw_org"] = {
        "type": "categorical",
        "values": [{"label": row[0] or "None", "count": row[1]} for row in cursor.fetchall()]
    }
    
    # Numeric fields - histogram data
    # Height distribution
    cursor = conn.execute("SELECT height FROM parts WHERE height IS NOT NULL")
    heights = [row[0] for row in cursor.fetchall()]
    if heights:
        distributions["height"] = {
            "type": "numeric",
            "values": heights,
            "min": min(heights),
            "max": max(heights),
            "mean": sum(heights) / len(heights)
        }
    
    # Stud count distribution
    cursor = conn.execute("SELECT studs_json FROM parts WHERE studs_json IS NOT NULL")
    stud_counts = []
    for row in cursor.fetchall():
        studs = json.loads(row[0]) if row[0] else []
        stud_counts.append(len(studs))
    
    if stud_counts:
        distributions["stud_count"] = {
            "type": "numeric",
            "values": stud_counts,
            "min": min(stud_counts),
            "max": max(stud_counts),
            "mean": sum(stud_counts) / len(stud_counts)
        }
    
    # Anti-stud count distribution
    cursor = conn.execute("SELECT anti_studs_json FROM parts WHERE anti_studs_json IS NOT NULL")
    anti_stud_counts = []
    for row in cursor.fetchall():
        anti_studs = json.loads(row[0]) if row[0] else []
        anti_stud_counts.append(len(anti_studs))
    
    if anti_stud_counts:
        distributions["anti_stud_count"] = {
            "type": "numeric",
            "values": anti_stud_counts,
            "min": min(anti_stud_counts),
            "max": max(anti_stud_counts),
            "mean": sum(anti_stud_counts) / len(anti_stud_counts)
        }
    
    # Technic hole count distribution
    cursor = conn.execute("SELECT technic_holes_json FROM parts WHERE technic_holes_json IS NOT NULL")
    technic_hole_counts = []
    for row in cursor.fetchall():
        technic_holes = json.loads(row[0]) if row[0] else []
        technic_hole_counts.append(len(technic_holes))
    
    if technic_hole_counts:
        distributions["technic_hole_count"] = {
            "type": "numeric",
            "values": technic_hole_counts,
            "min": min(technic_hole_counts),
            "max": max(technic_hole_counts),
            "mean": sum(technic_hole_counts) / len(technic_hole_counts)
        }
    
    return jsonify({"distributions": distributions})


@app.route('/api/stats')
def api_stats():
    """Get catalog statistics."""
    import json
    conn = get_db()
    
    # Overall stats
    stats = get_stats(conn)
    
    # Category breakdown
    cursor = conn.execute("""
        SELECT category, COUNT(*) as count,
               SUM(CASE WHEN has_image = 1 THEN 1 ELSE 0 END) as with_images
        FROM parts
        GROUP BY category
    """)
    categories = {}
    categories = {}
    for row in cursor.fetchall():
        # Handle null category
        cat_name = row[0] or "None"
        categories[cat_name] = {
            "count": row[1],
            "with_images": row[2]
        }
    
    # Connection point statistics
    cursor = conn.execute("""
        SELECT studs_json, anti_studs_json, technic_holes_json
        FROM parts
    """)
    
    total_studs = 0
    total_anti_studs = 0
    total_technic_holes = 0
    parts_with_studs = 0
    parts_with_anti_studs = 0
    parts_with_technic_holes = 0
    
    for row in cursor.fetchall():
        studs = json.loads(row[0]) if row[0] else []
        anti_studs = json.loads(row[1]) if row[1] else []
        technic_holes = json.loads(row[2]) if row[2] else []
        
        if studs:
            total_studs += len(studs)
            parts_with_studs += 1
        if anti_studs:
            total_anti_studs += len(anti_studs)
            parts_with_anti_studs += 1
        if technic_holes:
            total_technic_holes += len(technic_holes)
            parts_with_technic_holes += 1
    
    return jsonify({
        "total": stats["total"],
        "extraction": {
            "success": stats["success"],
            "partial": stats["partial"],
            "failed": stats["failed"]
        },
        "images": {
            "total_with_images": sum(c["with_images"] for c in categories.values()),
            "total_parts": stats["total"]
        },
        "categories": categories,
        "connections": {
            "total_studs": total_studs,
            "total_anti_studs": total_anti_studs,
            "total_technic_holes": total_technic_holes,
            "parts_with_studs": parts_with_studs,
            "parts_with_anti_studs": parts_with_anti_studs,
            "parts_with_technic_holes": parts_with_technic_holes
        }
    })


@app.route('/api/parts')
def api_parts():
    """Get paginated list of parts."""
    conn = get_db()
    
    # Query parameters - default to None (Missing = All)
    categories = request.args.get('categories')
    images = request.args.get('images')
    extractions = request.args.get('extractions')
    types = request.args.get('types')
    ldraw_orgs = request.args.get('ldraw_orgs')
    
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    offset = (page - 1) * limit
    
    # Build query
    where_clauses = []
    params = []
    
    # helper to check for explicit "select none"
    def is_none(val):
        return val == '_none_'

    # Handle categories (comma-separated)
    if categories is not None:
        if is_none(categories):
            where_clauses.append("1=0")
        elif categories:
            # Handle mixed usage of real categories and special "(No Category)"
            cat_list = [c.strip() for c in categories.split(',')]
            special_null = "(No Category)"
            
            real_cats = [c for c in cat_list if c != special_null]
            has_null = special_null in cat_list
            
            conditions = []
            if real_cats:
                placeholders = ','.join(['?' for _ in real_cats])
                conditions.append(f"category IN ({placeholders})")
                params.extend(real_cats)
            
            if has_null:
                conditions.append("category IS NULL")
                
            if conditions:
                where_clauses.append(f"({' OR '.join(conditions)})")
        
    # Handle types (comma-separated)
    # Logic: If param exists but empty -> Show All? No, frontend sends _none_ for none.
    # If param missing (e.g. first load) -> Show All.
    # If param has value -> Filter.
    if types is not None:
        if is_none(types):
             where_clauses.append("1=0")
        elif types:
            # Check for "_all_" just in case, though frontend should just omit it
            if types == '_all_':
                pass 
            else:
                type_list = [t.strip() for t in types.split(',')]
                # Special handling for "Other" or "Unknown" could go here if needed
                # For now assuming simple text match
                placeholders = ','.join(['?' for _ in type_list])
                where_clauses.append(f"type IN ({placeholders})")
                params.extend(type_list)
    
    # Handle ldraw_org (comma-separated)
    if ldraw_orgs is not None:
        if is_none(ldraw_orgs):
             where_clauses.append("1=0")
        elif ldraw_orgs:
            # Check for "_all_" just in case
            if ldraw_orgs == '_all_':
                pass 
            else:
                org_list = [o.strip() for o in ldraw_orgs.split(',')]
                
                # Check for explicit "None" string if used in frontend for nulls
                # Assuming "None" in the UI maps to NULL in DB for consistency with distribution
                special_null = "None"
                
                real_orgs = [o for o in org_list if o != special_null]
                has_null = special_null in org_list
                
                conditions = []
                if real_orgs:
                    placeholders = ','.join(['?' for _ in real_orgs])
                    conditions.append(f"ldraw_org IN ({placeholders})")
                    params.extend(real_orgs)
                
                if has_null:
                    conditions.append("ldraw_org IS NULL")
                
                if conditions:
                    where_clauses.append(f"({' OR '.join(conditions)})")

    # Handle images (comma-separated: yes, no)
    if images is not None:
        if is_none(images):
            where_clauses.append("1=0")
        elif images:
            image_list = [i.strip() for i in images.split(',')]
            image_conditions = []
            if 'yes' in image_list:
                image_conditions.append("has_image = 1")
            if 'no' in image_list:
                image_conditions.append("has_image = 0")
            if image_conditions:
                where_clauses.append(f"({' OR '.join(image_conditions)})")
    
    # Handle extractions (comma-separated)
    if extractions is not None:
        if is_none(extractions):
            where_clauses.append("1=0")
        elif extractions:
            extraction_list = [e.strip() for e in extractions.split(',')]
            placeholders = ','.join(['?' for _ in extraction_list])
            where_clauses.append(f"extraction_status IN ({placeholders})")
            params.extend(extraction_list)
    
    # Handle search (search both part_id and part_name)
    if search:
        where_clauses.append("(part_id LIKE ? OR part_name LIKE ?)")
        params.append(f"%{search}%")
        params.append(f"%{search}%")
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Get total count
    cursor = conn.execute(f"SELECT COUNT(*) FROM parts WHERE {where_sql}", params)
    total = cursor.fetchone()[0]
    
    # Get parts
    cursor = conn.execute(f"""
        SELECT part_id, part_name, type, category, ldraw_org, height, has_image, image_path, extraction_status,
               studs_json, anti_studs_json, technic_holes_json
        FROM parts
        WHERE {where_sql}
        ORDER BY part_id
        LIMIT ? OFFSET ?
    """, params + [limit, offset])
    
    parts = []
    for row in cursor.fetchall():
        import json
        # Indices based on: part_id(0), part_name(1), type(2), category(3), ldraw_org(4), 
        # height(5), has_image(6), image_path(7), extraction_status(8), 
        # studs_json(9), anti_studs_json(10), technic_holes_json(11)
        studs = json.loads(row[9]) if row[9] else []
        anti_studs = json.loads(row[10]) if row[10] else []
        technic_holes = json.loads(row[11]) if row[11] else []
        
        parts.append({
            "part_id": row[0],
            "part_name": row[1] or row[0],
            "type": row[2],
            "category": row[3],
            "ldraw_org": row[4],
            "height": row[5],
            "has_image": bool(row[6]),
            "image_path": row[7],
            "extraction_status": row[8],
            "stud_count": len(studs),
            "anti_stud_count": len(anti_studs),
            "technic_hole_count": len(technic_holes)
        })
    
    return jsonify({
        "parts": parts,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    })


@app.route('/api/parts/<part_id>')
def api_part_detail(part_id):
    """Get detailed info for a single part."""
    from validator.config import get_parts_dir
    conn = get_db()
    part = load_part(conn, part_id)
    
    if not part:
        return jsonify({"error": "Part not found"}), 404
    
    # Try to load raw LDraw content
    raw_content = ""
    try:
        part_path = get_parts_dir() / f"{part_id}.dat"
        if part_path.exists():
            with open(part_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_content = f.read()
    except Exception as e:
        raw_content = f"Error loading file: {str(e)}"
    
    return jsonify({
        "part_id": part.part_id,
        "part_name": part.part_name,
        "category": part.category,
        "height": part.height,
        "bounds": part.bounds,
        "studs": part.studs,
        "anti_studs": part.anti_studs,
        "technic_holes": part.technic_holes,
        "extraction_status": part.extraction_status,
        "raw_content": raw_content
    })


@app.route('/api/images/<part_id>.png')
def api_image(part_id):
    """Serve part image (from LDraw or placeholder)."""
    conn = get_db()
    cursor = conn.execute("SELECT image_path, has_image FROM parts WHERE part_id = ?", (part_id,))
    row = cursor.fetchone()
    
    if row and row[1]:  # has_image = True
        path_str = row[0]
        if path_str:
            project_root = Path(__file__).parent.parent
            image_path = Path(path_str)
            
            if not image_path.is_absolute():
                image_path = project_root / path_str
                
            if image_path.exists():
                return send_file(image_path, mimetype='image/png')
    
    # Check if we have it in the new rendered location even if DB is not updated (fallback)
    manual_render_path = Path(__file__).parent.parent / "data" / "rendered_images" / f"{part_id}.png"
    if manual_render_path.exists():
        return send_file(manual_render_path, mimetype='image/png')

    # Return placeholder
    placeholder = Path(__file__).parent / "static" / "placeholder.png"
    if placeholder.exists():
        return send_file(placeholder, mimetype='image/png')
    else:
        return "No image", 404


@app.route('/api/parts/<part_id>/ldraw')
def api_part_ldraw(part_id):
    """Serve raw LDraw file content for 3D viewing."""
    from validator.config import get_parts_dir
    
    # Try to find the part file
    parts_dir = get_parts_dir()
    part_file = parts_dir / f"{part_id}.dat"
    
    if not part_file.exists():
        return jsonify({"error": "LDraw file not found"}), 404
    
    try:
        with open(part_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return Response(content, mimetype='text/plain')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/parts/<part_id>/render', methods=['POST'])
def api_render_part(part_id):
    """Render a part image on-demand using LDView."""
    from validator.scene_graph import SceneGraph, Placement
    from validator.renderer import render_scene
    import json
    
    conn = get_db()
    
    # Check if part exists
    part = load_part(conn, part_id)
    if not part:
        return jsonify({"error": "Part not found"}), 404
    
    try:
        # Create scene with single part
        sg = SceneGraph()
        sg.add_placement(Placement(
            part_id=part_id,
            color=16,  # Main color (default)
            position=(0.0, 0.0, 0.0),
            rotation=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        ))
        
        # Render to file
        project_root = Path(__file__).parent.parent
        output_dir = project_root / "data" / "rendered_images"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{part_id}.png"
        
        print(f"[RENDER] Attempting to render {part_id} to {output_path}")
        success = render_scene(sg, str(output_path), width=400, height=400)
        
        if not success:
            print(f"[RENDER] Failed to render {part_id}")
            return jsonify({
                "success": False,
                "error": "LDView rendering failed"
            }), 500
        
        # Check if file was created
        if not output_path.exists():
            print(f"[RENDER] Output file not created: {output_path}")
            return jsonify({
                "success": False,
                "error": "Output file not created"
            }), 500
        
        print(f"[RENDER] Successfully rendered {part_id}, file size: {output_path.stat().st_size} bytes")
        
        # Update database
        rel_path = f"data/rendered_images/{part_id}.png"
        conn.execute(
            "UPDATE parts SET has_image = 1, image_path = ? WHERE part_id = ?",
            (rel_path, part_id)
        )
        conn.commit()
        
        return jsonify({
            "success": True,
            "message": f"Rendered {part_id}",
            "image_url": f"/api/images/{part_id}.png"
        })
        
    except Exception as e:
        import traceback
        print(f"[RENDER] Exception: {e}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    print("Starting LDraw Catalog Viewer...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
