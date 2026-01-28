# Sitemap Screenshot Tool

A Python tool that takes full page screenshots of all pages listed in a website sitemap.

## Features

- ✅ **Web Interface** - Beautiful UI for easy screenshot management
- ✅ **Auto-discovers sitemaps** - Just provide a homepage URL!
- ✅ Parses standard sitemap.xml files
- ✅ Supports sitemap index files (nested sitemaps)
- ✅ Works with local files or remote URLs
- ✅ Full page screenshots (captures entire page, not just viewport)
- ✅ Automatic filename generation from URLs
- ✅ Resume capability (start from specific index)
- ✅ Progress tracking and error handling
- ✅ Real-time progress updates in web interface

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

## Web Interface

The tool includes a beautiful web interface for easy use:

1. Start the web server:
```bash
python app.py
```

2. Open your browser to `http://localhost:5000`

3. Enter a URL and choose:
   - **Single URL**: Screenshot just one page
   - **Entire Website**: Auto-discover sitemap and screenshot all pages

The interface shows real-time progress and displays all screenshots when complete!

## Usage

### Basic Usage

**Just provide a homepage URL - the tool will automatically find the sitemap:**
```bash
python screenshot_sitemap.py https://example.com
```

Or provide a sitemap URL directly:
```bash
python screenshot_sitemap.py https://example.com/sitemap.xml
```

Or use a local sitemap file:
```bash
python screenshot_sitemap.py sitemap.xml
```

### Options

- `-o, --output DIR`: Specify output directory (default: `screenshots`)
- `--no-headless`: Run browser in visible mode (useful for debugging)
- `-w, --wait-time SECONDS`: Wait time after page load (default: 2)
- `--max-pages N`: Limit to first N pages
- `--start-from N`: Start from index N (useful for resuming)

### Examples

**Custom output directory:**
```bash
python screenshot_sitemap.py https://example.com -o my_screenshots
```

**Run with visible browser:**
```bash
python screenshot_sitemap.py https://example.com --no-headless
```

**Limit to first 10 pages:**
```bash
python screenshot_sitemap.py https://example.com --max-pages 10
```

**Resume from page 50:**
```bash
python screenshot_sitemap.py https://example.com --start-from 50
```

**Longer wait time for slow-loading pages:**
```bash
python screenshot_sitemap.py https://example.com -w 5
```

## Output

Screenshots are saved as PNG files in the output directory. Filenames are automatically generated from URLs:
- `example.com_index.png` for the homepage
- `example.com_about_us.png` for `/about-us`
- `example.com_products_item_123.png` for `/products/item/123`

## How It Works

1. If you provide a homepage URL, automatically discovers the sitemap by checking:
   - `/sitemap.xml`
   - `/sitemap_index.xml`
   - `/sitemap/sitemap.xml`
   - `/sitemaps/sitemap.xml`
   - `robots.txt` for sitemap references
2. Parses the sitemap XML file (supports standard format and sitemap indexes)
3. Extracts all URLs from the sitemap
4. Launches a headless Chromium browser
5. Navigates to each URL and waits for the page to load
6. Takes a full page screenshot (captures entire scrollable content)
7. Saves screenshots with organized filenames

## Notes

- The tool waits for `networkidle` before taking screenshots to ensure pages are fully loaded
- Full page screenshots capture the entire scrollable content, not just the viewport
- Failed screenshots are logged but don't stop the process
- Large sitemaps may take a while - use `--max-pages` to test with a subset first
