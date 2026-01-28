#!/usr/bin/env python3
"""
Flask web server for the screenshot tool
"""

import os
import subprocess
import threading
import json
import zipfile
import shutil
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from flask_cors import CORS

# Determine template and static folders based on environment
if os.environ.get('VERCEL') == '1':
    # In Vercel, paths are relative to the api directory
    template_folder = str(Path(__file__).parent.parent / 'templates')
    static_folder = str(Path(__file__).parent.parent / 'static')
else:
    template_folder = 'templates'
    static_folder = 'static'

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
CORS(app)

# Get the directory where this script is located
BASE_DIR = Path(__file__).parent.resolve()
# In Vercel, use /tmp for writable storage
if os.environ.get('VERCEL') == '1':
    SCREENSHOTS_DIR = Path('/tmp') / "screenshots"
else:
    SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Store running processes
running_tasks = {}


def run_screenshot_task(task_id, url, mode, output_dir):
    """Run screenshot task in background"""
    try:
        script_path = BASE_DIR / "screenshot_sitemap.py"
        venv_python = BASE_DIR / "venv" / "bin" / "python"
        
        # Use venv python if it exists, otherwise use system python
        if venv_python.exists():
            python_cmd = str(venv_python)
        else:
            python_cmd = "python3"
        
        if mode == "single":
            cmd = [python_cmd, str(script_path), "--url", url, "-o", output_dir]
        else:  # entire website
            cmd = [python_cmd, str(script_path), url, "-o", output_dir]
        
        # Run the command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(BASE_DIR)
        )
        
        # Store process
        running_tasks[task_id] = {
            "process": process,
            "status": "running",
            "output": []
        }
        
        # Read output line by line
        for line in process.stdout:
            line = line.strip()
            if line:
                running_tasks[task_id]["output"].append(line)
                # Keep only last 100 lines
                if len(running_tasks[task_id]["output"]) > 100:
                    running_tasks[task_id]["output"].pop(0)
        
        # Wait for process to complete
        process.wait()
        
        # Count screenshots
        screenshot_count = len(list(Path(output_dir).glob("*.png")))
        
        running_tasks[task_id]["status"] = "completed"
        running_tasks[task_id]["screenshot_count"] = screenshot_count
        
    except Exception as e:
        running_tasks[task_id]["status"] = "error"
        running_tasks[task_id]["error"] = str(e)


@app.route('/')
def index():
    """Serve the main page"""
    # Check if running on Vercel
    is_vercel = os.environ.get('VERCEL') == '1'
    return render_template('index.html', is_vercel=is_vercel)


@app.route('/api/screenshot', methods=['POST'])
def start_screenshot():
    """Start a screenshot task"""
    # Check if running on Vercel
    if os.environ.get('VERCEL') == '1':
        return jsonify({
            "error": "Screenshot functionality is not available on Vercel",
            "message": "Playwright requires browser binaries and longer execution times than Vercel's serverless functions support. Please use a platform like Railway, Render, or Fly.io for full functionality.",
            "suggestion": "Deploy to Railway.app or Render.com for full screenshot capabilities"
        }), 503
    
    data = request.json
    url = data.get('url', '').strip()
    mode = data.get('mode', 'single')  # 'single' or 'entire'
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    # Create unique task ID
    import uuid
    task_id = str(uuid.uuid4())
    
    # Create output directory for this task
    output_dir = str(SCREENSHOTS_DIR / task_id)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Start background task
    thread = threading.Thread(
        target=run_screenshot_task,
        args=(task_id, url, mode, output_dir)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "task_id": task_id,
        "status": "started",
        "output_dir": task_id
    })


@app.route('/api/status/<task_id>')
def get_status(task_id):
    """Get status of a screenshot task"""
    if task_id not in running_tasks:
        return jsonify({"error": "Task not found"}), 404
    
    task = running_tasks[task_id]
    response = {
        "status": task["status"],
        "output": task.get("output", [])[-20:],  # Last 20 lines
        "screenshot_count": task.get("screenshot_count", 0)
    }
    
    if "error" in task:
        response["error"] = task["error"]
    
    return jsonify(response)


@app.route('/api/screenshots/<task_id>')
def list_screenshots(task_id):
    """List screenshots for a task"""
    task_dir = SCREENSHOTS_DIR / task_id
    if not task_dir.exists():
        return jsonify({"error": "Task directory not found"}), 404
    
    screenshots = []
    for png_file in sorted(task_dir.glob("*.png")):
        screenshots.append({
            "filename": png_file.name,
            "size": png_file.stat().st_size
        })
    
    return jsonify({"screenshots": screenshots})


@app.route('/api/screenshots/<task_id>/<filename>')
def get_screenshot(task_id, filename):
    """Serve a screenshot file"""
    task_dir = SCREENSHOTS_DIR / task_id
    if not task_dir.exists():
        return jsonify({"error": "Task directory not found"}), 404
    
    return send_from_directory(str(task_dir), filename)


@app.route('/api/download/<task_id>/<filename>')
def download_screenshot(task_id, filename):
    """Download a single screenshot file"""
    task_dir = SCREENSHOTS_DIR / task_id
    if not task_dir.exists():
        return jsonify({"error": "Task directory not found"}), 404
    
    file_path = task_dir / filename
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=filename,
        mimetype='image/png'
    )


@app.route('/api/download-all/<task_id>')
def download_all(task_id):
    """Download all screenshots as a zip file"""
    task_dir = SCREENSHOTS_DIR / task_id
    if not task_dir.exists():
        return jsonify({"error": "Task directory not found"}), 404
    
    # Get all PNG files
    png_files = list(sorted(task_dir.glob("*.png")))
    if not png_files:
        return jsonify({"error": "No screenshots found"}), 404
    
    # Create zip file
    zip_path = SCREENSHOTS_DIR / f"{task_id}.zip"
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for png_file in png_files:
                zipf.write(png_file, png_file.name)
        
        return send_file(
            str(zip_path),
            as_attachment=True,
            download_name=f"screenshots_{task_id}.zip",
            mimetype='application/zip'
        )
    except Exception as e:
        return jsonify({"error": f"Failed to create zip file: {str(e)}"}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    print("Starting screenshot web server...")
    print(f"Open http://localhost:{port} in your browser")
    app.run(debug=debug, host='0.0.0.0', port=port)
