#!/usr/bin/env python3
"""
Quick script to screenshot a single URL
"""

import sys
from pathlib import Path
from screenshot_sitemap import take_screenshot
from playwright.sync_api import sync_playwright

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python screenshot_url.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    output_dir = Path("screenshots")
    output_dir.mkdir(exist_ok=True)
    
    print(f"Screenshotting: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        result = take_screenshot(page, url, output_dir, wait_time=3)
        
        browser.close()
        
        if result:
            print(f"\n✓ Screenshot saved: {result}")
        else:
            print("\n✗ Failed to take screenshot")
