#!/usr/bin/env python3
"""
Sitemap Screenshot Tool
Takes full page screenshots of all pages listed in a website sitemap.
"""

import argparse
import os
import sys
import time
import urllib.parse
from pathlib import Path
from typing import List, Optional
import xml.etree.ElementTree as ET

from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError


def discover_sitemap(homepage_url: str) -> Optional[str]:
    """
    Try to discover the sitemap URL from a homepage.
    
    Checks common sitemap locations:
    - /sitemap.xml
    - /sitemap_index.xml
    - /sitemap/sitemap.xml
    - /sitemaps/sitemap.xml
    - robots.txt (for sitemap reference)
    
    Args:
        homepage_url: Homepage URL
        
    Returns:
        Sitemap URL if found, None otherwise
    """
    import urllib.request
    import urllib.error
    
    parsed = urllib.parse.urlparse(homepage_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Common sitemap locations
    sitemap_paths = [
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/sitemap/sitemap.xml',
        '/sitemaps/sitemap.xml',
        '/sitemap1.xml',
    ]
    
    print(f"Looking for sitemap at {base_url}...")
    
    # Try common sitemap locations
    for path in sitemap_paths:
        sitemap_url = base_url + path
        try:
            req = urllib.request.Request(sitemap_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (compatible; SitemapBot/1.0)')
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    # Verify it's actually XML
                    content = response.read(1024).decode('utf-8', errors='ignore')
                    if '<?xml' in content or '<urlset' in content or '<sitemapindex' in content:
                        print(f"  ✓ Found sitemap at: {sitemap_url}")
                        return sitemap_url
        except (urllib.error.HTTPError, urllib.error.URLError, Exception):
            continue
    
    # Try checking robots.txt for sitemap reference
    robots_url = base_url + '/robots.txt'
    try:
        req = urllib.request.Request(robots_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (compatible; SitemapBot/1.0)')
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                content = response.read().decode('utf-8', errors='ignore')
                for line in content.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        print(f"  ✓ Found sitemap in robots.txt: {sitemap_url}")
                        # Verify it exists
                        try:
                            req2 = urllib.request.Request(sitemap_url)
                            req2.add_header('User-Agent', 'Mozilla/5.0 (compatible; SitemapBot/1.0)')
                            with urllib.request.urlopen(req2, timeout=10) as response2:
                                if response2.status == 200:
                                    return sitemap_url
                        except:
                            continue
    except:
        pass
    
    return None


def parse_sitemap(sitemap_path: str) -> List[str]:
    """
    Parse a sitemap XML file and extract all URLs.
    
    Supports:
    - Standard sitemap.xml format
    - Sitemap index files (that reference other sitemaps)
    - Local files or URLs
    
    Args:
        sitemap_path: Path to sitemap file or URL
        
    Returns:
        List of URLs to screenshot
    """
    urls = []
    
    # Fetch sitemap content
    if sitemap_path.startswith(('http://', 'https://')):
        import urllib.request
        req = urllib.request.Request(sitemap_path)
        req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
    else:
        with open(sitemap_path, 'rb') as f:
            content = f.read()
    
    # Parse XML
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"Error parsing sitemap XML: {e}")
        sys.exit(1)
    
    # Handle namespace
    namespaces = {
        'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'
    }
    
    # Check if this is a sitemap index
    sitemapindex = root.findall('.//ns:sitemap', namespaces)
    if sitemapindex:
        print(f"Found sitemap index with {len(sitemapindex)} sitemaps")
        for sitemap in sitemapindex:
            loc = sitemap.find('ns:loc', namespaces)
            if loc is not None and loc.text:
                print(f"  Fetching nested sitemap: {loc.text}")
                nested_urls = parse_sitemap(loc.text)
                urls.extend(nested_urls)
    else:
        # Regular sitemap - extract URLs
        url_elements = root.findall('.//ns:url', namespaces)
        for url_elem in url_elements:
            loc = url_elem.find('ns:loc', namespaces)
            if loc is not None and loc.text:
                urls.append(loc.text.strip())
    
    return urls


def sanitize_filename(url: str) -> str:
    """
    Convert a URL to a safe filename.
    
    Args:
        url: URL to convert
        
    Returns:
        Safe filename string
    """
    # Parse URL
    parsed = urllib.parse.urlparse(url)
    
    # Get path and remove leading/trailing slashes
    path = parsed.path.strip('/')
    
    # Replace slashes and other problematic chars
    if not path:
        path = 'index'
    
    # Replace problematic characters
    filename = path.replace('/', '_').replace('?', '_').replace('&', '_')
    filename = filename.replace('=', '_').replace(':', '_')
    
    # Add domain prefix if needed for uniqueness
    domain = parsed.netloc.replace('www.', '').replace('.', '_')
    
    # Limit filename length
    if len(filename) > 200:
        filename = filename[:200]
    
    return f"{domain}_{filename}" if filename != 'index' else f"{domain}_index"


def take_screenshot(page: Page, url: str, output_dir: Path, wait_time: int = 2) -> Optional[str]:
    """
    Navigate to a URL and take a full page screenshot.
    
    Args:
        page: Playwright page object
        url: URL to screenshot
        output_dir: Directory to save screenshot
        wait_time: Seconds to wait after page load
        
    Returns:
        Path to saved screenshot or None if failed
    """
    try:
        print(f"  Navigating to: {url}")
        # Use 'load' to ensure DOM and resources are loaded
        page.goto(url, wait_until='load', timeout=60000)
        
        # Wait for network to be idle (no requests for 500ms)
        try:
            page.wait_for_load_state('networkidle', timeout=30000)
        except:
            pass  # Continue even if networkidle times out
        
        # Wait for page to fully render
        time.sleep(wait_time)
        
        # Scroll through the entire page to trigger lazy-loaded content
        # This ensures all sections are loaded before screenshot
        print(f"  Scrolling page to load all content...", end='', flush=True)
        viewport_height = page.viewport_size['height']
        
        # Get initial height
        current_height = page.evaluate("document.body.scrollHeight")
        previous_height = 0
        scroll_position = 0
        iterations = 0
        max_iterations = 15  # Reduced from 20
        
        # Quick scroll to bottom first to trigger lazy loading
        page.evaluate(f"window.scrollTo(0, {current_height})")
        time.sleep(0.5)
        
        # Now scroll incrementally to ensure everything loads
        while iterations < max_iterations and scroll_position < current_height:
            page.evaluate(f"window.scrollTo(0, {scroll_position})")
            time.sleep(0.15)  # Reduced from 0.3s
            
            # Check if height changed
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height > current_height:
                current_height = new_height
            
            # Move scroll position
            scroll_position += viewport_height * 0.8
            
            iterations += 1
            if iterations % 3 == 0:
                print(".", end='', flush=True)
        
        # Final scroll to bottom
        page.evaluate(f"window.scrollTo(0, {current_height})")
        time.sleep(0.3)
        
        # Scroll back to top
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(0.3)
        print(" done")
        
        # Wait for images to load (with timeout)
        print(f"  Waiting for images...", end='', flush=True)
        try:
            page.wait_for_function("""
                () => {
                    const images = Array.from(document.images);
                    return images.every(img => img.complete || img.naturalHeight > 0);
                }
            """, timeout=5000)
        except:
            pass  # Continue even if timeout
        
        # Quick wait for any CSS transitions/animations
        time.sleep(0.3)
        
        # Additional wait for any remaining dynamic content
        time.sleep(wait_time)
        print(" done")
        
        # Generate filename
        filename = sanitize_filename(url)
        screenshot_path = output_dir / f"{filename}.png"
        
        # Take full page screenshot
        page.screenshot(path=str(screenshot_path), full_page=True)
        
        print(f"  ✓ Saved: {screenshot_path.name}")
        return str(screenshot_path)
        
    except PlaywrightTimeoutError:
        print(f"  ✗ Timeout loading: {url}")
        return None
    except Exception as e:
        print(f"  ✗ Error screenshotting {url}: {e}")
        return None


def screenshot_sitemap(
    sitemap_path: str,
    output_dir: str = "screenshots",
    headless: bool = True,
    wait_time: int = 2,
    max_pages: Optional[int] = None,
    start_from: int = 0
):
    """
    Main function to screenshot all pages in a sitemap.
    
    Args:
        sitemap_path: Path to sitemap file, sitemap URL, or homepage URL
        output_dir: Directory to save screenshots
        headless: Run browser in headless mode
        wait_time: Seconds to wait after each page load
        max_pages: Maximum number of pages to screenshot (None for all)
        start_from: Index to start from (for resuming)
    """
    # Check if input is a homepage URL (not a sitemap)
    actual_sitemap_path = sitemap_path
    
    # If it's a URL and doesn't look like a sitemap, try to discover it
    if sitemap_path.startswith(('http://', 'https://')):
        # Check if it's already a sitemap URL
        if not any(x in sitemap_path.lower() for x in ['sitemap', '.xml']):
            # Looks like a homepage, try to discover sitemap
            discovered = discover_sitemap(sitemap_path)
            if discovered:
                actual_sitemap_path = discovered
            else:
                print(f"\n⚠️  Could not automatically find sitemap for {sitemap_path}")
                print("   Tried common locations: /sitemap.xml, /sitemap_index.xml, etc.")
                print("   Please provide the sitemap URL directly, or ensure the site has a sitemap.")
                sys.exit(1)
    
    # Parse sitemap
    print(f"\nParsing sitemap: {actual_sitemap_path}")
    urls = parse_sitemap(actual_sitemap_path)
    
    if not urls:
        print("No URLs found in sitemap!")
        return
    
    print(f"Found {len(urls)} URLs in sitemap")
    
    # Apply limits
    if start_from > 0:
        urls = urls[start_from:]
        print(f"Starting from index {start_from}")
    
    if max_pages:
        urls = urls[:max_pages]
        print(f"Limiting to {max_pages} pages")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"Saving screenshots to: {output_path.absolute()}")
    
    # Launch browser
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        # Screenshot each URL
        successful = 0
        failed = 0
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing: {url}")
            result = take_screenshot(page, url, output_path, wait_time)
            
            if result:
                successful += 1
            else:
                failed += 1
        
        browser.close()
        
        # Summary
        print(f"\n{'='*60}")
        print(f"Complete!")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"  Total: {len(urls)}")
        print(f"  Screenshots saved to: {output_path.absolute()}")


def main():
    parser = argparse.ArgumentParser(
        description='Take full page screenshots of all pages in a sitemap',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Just provide homepage URL - will auto-discover sitemap
  python screenshot_sitemap.py https://example.com

  # Screenshot from a remote sitemap URL
  python screenshot_sitemap.py https://example.com/sitemap.xml

  # Screenshot from a local sitemap file
  python screenshot_sitemap.py sitemap.xml

  # Custom output directory
  python screenshot_sitemap.py https://example.com -o my_screenshots

  # Run with visible browser
  python screenshot_sitemap.py https://example.com --no-headless

  # Limit to first 10 pages
  python screenshot_sitemap.py https://example.com --max-pages 10

  # Resume from page 50
  python screenshot_sitemap.py https://example.com --start-from 50
        """
    )
    
    parser.add_argument(
        'sitemap',
        nargs='?',
        help='Path to sitemap XML file, sitemap URL, or homepage URL (will auto-discover sitemap)'
    )
    
    parser.add_argument(
        '--url',
        help='Screenshot a single URL directly (bypasses sitemap)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='screenshots',
        help='Output directory for screenshots (default: screenshots)'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Run browser in visible mode (default: headless)'
    )
    
    parser.add_argument(
        '-w', '--wait-time',
        type=int,
        default=2,
        help='Seconds to wait after page load (default: 2)'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        default=None,
        help='Maximum number of pages to screenshot (default: all)'
    )
    
    parser.add_argument(
        '--start-from',
        type=int,
        default=0,
        help='Start from this index (useful for resuming)'
    )
    
    args = parser.parse_args()
    
    # If --url flag is used, screenshot just that URL
    if args.url:
        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Screenshotting single URL: {args.url}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not args.no_headless)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            result = take_screenshot(page, args.url, output_path, args.wait_time)
            browser.close()
            
            if result:
                print(f"\n✓ Screenshot saved: {result}")
            else:
                print("\n✗ Failed to take screenshot")
                sys.exit(1)
    elif args.sitemap:
        screenshot_sitemap(
            sitemap_path=args.sitemap,
            output_dir=args.output,
            headless=not args.no_headless,
            wait_time=args.wait_time,
            max_pages=args.max_pages,
            start_from=args.start_from
        )
    else:
        parser.error("Either provide a sitemap/homepage URL or use --url to screenshot a single URL")


if __name__ == '__main__':
    main()
