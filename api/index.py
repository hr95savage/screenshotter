"""
Vercel serverless function wrapper for Flask app
Note: Playwright may not work in Vercel's serverless environment
due to browser binary requirements and execution time limits.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from app import app
    
    # Export the Flask app for Vercel
    handler = app
except Exception as e:
    # Fallback handler if app import fails
    from flask import Flask, jsonify
    fallback_app = Flask(__name__)
    
    @fallback_app.route('/')
    def index():
        return jsonify({
            "error": "App initialization failed",
            "message": str(e),
            "note": "Playwright requires special setup in serverless environments"
        }), 500
    
    @fallback_app.route('/<path:path>')
    def catch_all(path):
        return jsonify({
            "error": "App initialization failed",
            "message": str(e)
        }), 500
    
    handler = fallback_app
