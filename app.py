#!/usr/bin/env python3
"""
Flask web server for the screenshot tool
"""

import logging
import os
import subprocess
import sys
import threading
import traceback
import zipfile
from pathlib import Path
from flask import Flask, Response, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

BASE_DIR = Path(__file__).parent.resolve()
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Store running processes
running_tasks = {}


def run_screenshot_task(task_id, url, mode, output_dir, url_list=None):
    """Run screenshot task in background. For mode 'list', url_list is a list of URL strings."""
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
        elif mode == "list" and url_list:
            urls_file = Path(output_dir) / "urls.txt"
            with open(urls_file, "w", encoding="utf-8") as f:
                for u in url_list:
                    u = (u or "").strip()
                    if u and (u.startswith("http://") or u.startswith("https://")):
                        f.write(u + "\n")
            cmd = [python_cmd, str(script_path), "--urls-file", str(urls_file), "-o", output_dir]
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
                # Keep last 3000 lines
                if len(running_tasks[task_id]["output"]) > 3000:
                    running_tasks[task_id]["output"].pop(0)
        
        # Wait for process to complete
        process.wait()
        
        # Count screenshots
        screenshot_count = len(list(Path(output_dir).glob("*.png")))
        
        if process.returncode != 0:
            running_tasks[task_id]["status"] = "error"
            last_output = running_tasks[task_id]["output"][-15:] if running_tasks[task_id]["output"] else []
            err_msg = f"Process exited with code {process.returncode}."
            if last_output:
                err_msg += " Last output:\n" + "\n".join(last_output)
            running_tasks[task_id]["error"] = err_msg
            logger.error("Screenshot task %s failed: %s", task_id, err_msg)
        else:
            running_tasks[task_id]["status"] = "completed"
            running_tasks[task_id]["screenshot_count"] = screenshot_count
        
    except Exception as e:
        tb_lines = traceback.format_exc().strip().split("\n")
        if task_id not in running_tasks:
            running_tasks[task_id] = {"status": "error", "error": str(e), "output": [f"Exception: {e}"] + tb_lines}
        else:
            running_tasks[task_id]["status"] = "error"
            running_tasks[task_id]["error"] = str(e)
            running_tasks[task_id].setdefault("output", []).extend([f"Exception: {e}"] + tb_lines)
        logger.exception("Screenshot task %s raised exception", task_id)


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/screenshot', methods=['POST'])
def start_screenshot():
    """Start a screenshot task"""
    data = request.json
    url = (data.get('url') or '').strip()
    mode = data.get('mode', 'single')  # 'single', 'entire', or 'list'
    url_list = data.get('urls')  # for mode 'list': list of URL strings
    
    if mode == 'list':
        if not url_list or not isinstance(url_list, list):
            return jsonify({"error": "List mode requires 'urls' (array of URLs)"}), 400
        # Normalize: strings only, strip, require http(s)
        url_list = [u.strip() for u in url_list if isinstance(u, str) and u.strip().startswith(('http://', 'https://'))]
        if not url_list:
            return jsonify({"error": "Provide at least one valid URL (http:// or https://) in the list"}), 400
    elif not url:
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
        args=(task_id, url, mode, output_dir),
        kwargs={'url_list': url_list if mode == 'list' else None}
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
        "output": task.get("output", [])[-1500:],  # Last 1500 lines
        "screenshot_count": task.get("screenshot_count", 0)
    }
    
    if "error" in task:
        response["error"] = task["error"]
    
    return jsonify(response)


@app.route('/api/log/<task_id>')
def get_log(task_id):
    """Return full run log as plain text (for download)."""
    if task_id not in running_tasks:
        return jsonify({"error": "Task not found"}), 404
    lines = running_tasks[task_id].get("output", [])
    text = "\n".join(lines) if lines else "(no log output)"
    return Response(
        text,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename=screenshot_log_{task_id}.txt"},
    )


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
