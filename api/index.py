"""
Vercel serverless function wrapper for Flask app
Note: Playwright may not work in Vercel's serverless environment
due to browser binary requirements and execution time limits.
"""

from app import app

# Export the Flask app for Vercel
handler = app
