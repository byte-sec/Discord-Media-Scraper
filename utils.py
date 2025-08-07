import logging
import os
import json
from datetime import datetime
import re
import random
import html
import math
import sqlite3

from config import PROXIES_FILE, DOWNLOADED_TRACKER_FILE, DOWNLOAD_DIR
from moviepy import VideoFileClip # Using the corrected import

# Database file path is now built using your config
DATABASE_FILE = os.path.join(DOWNLOAD_DIR, "sql_database", "metadata.db")

def init_database():
    """Creates the database and the 'videos' table if they don't exist."""
    try:
        os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)
        con = sqlite3.connect(DATABASE_FILE)
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                download_filename TEXT PRIMARY KEY,
                message_id TEXT,
                channel_id TEXT,
                author_id TEXT,
                author_name TEXT,
                timestamp TEXT,
                prompt TEXT,
                attachment_json TEXT,
                discord_message_url TEXT
            )
        """)
        con.commit()
        con.close()
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")
        raise

def save_metadata_to_db(metadata: dict):
    """Saves a single video's metadata to the SQLite database."""
    try:
        con = sqlite3.connect(DATABASE_FILE)
        cur = con.cursor()
        
        params = {
            "download_filename": metadata.get("download_filename"),
            "message_id": metadata.get("message_id"),
            "channel_id": metadata.get("channel_id"),
            "author_id": metadata.get("author", {}).get("id"),
            "author_name": metadata.get("author", {}).get("username"),
            "timestamp": metadata.get("timestamp"),
            "prompt": metadata.get("prompt"),
            "attachment_json": json.dumps(metadata.get("original_attachment")),
            "discord_message_url": metadata.get("discord_message_url")
        }
        
        cur.execute("""
            INSERT OR REPLACE INTO videos (
                download_filename, message_id, channel_id, author_id, author_name, 
                timestamp, prompt, attachment_json, discord_message_url
            ) VALUES (
                :download_filename, :message_id, :channel_id, :author_id, :author_name, 
                :timestamp, :prompt, :attachment_json, :discord_message_url
            )
        """, params)
        
        con.commit()
        con.close()
    except Exception as e:
        logging.error(f"Failed to save metadata to database for {metadata.get('download_filename')}: {e}")

# --- UNCHANGED FUNCTIONS ---
def load_proxies_from_file(filename: str = PROXIES_FILE) -> list[str]:
    # ... (this function is unchanged)
    proxies = []
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                for line in f:
                    proxy = line.strip()
                    if proxy and not proxy.startswith("#"):
                        if not re.match(r"^(http|https|socks5)://", proxy):
                            proxy = "http://" + proxy
                        proxies.append(proxy)
            logging.info(f"Loaded {len(proxies)} proxies from {filename}.")
        else:
            logging.info(f"Proxy file '{filename}' not found. No proxies loaded.")
    except Exception as e:
        logging.error(f"Error loading proxies from file: {e}")
    return proxies

def save_proxies_to_file(proxies: list[str], filename: str = PROXIES_FILE):
    # ... (this function is unchanged)
    try:
        with open(filename, "w") as f:
            for proxy in proxies:
                f.write(proxy + "\n")
        logging.info(f"Saved {len(proxies)} proxies to {filename}.")
    except Exception as e:
        logging.error(f"Error saving proxies to file: {e}")

def load_downloaded_attachments() -> set[str]:
    # ... (this function is unchanged)
    try:
        if os.path.exists(DOWNLOADED_TRACKER_FILE):
            with open(DOWNLOADED_TRACKER_FILE, "r") as f:
                return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning(f"Downloaded tracker file '{DOWNLOADED_TRACKER_FILE}' is missing or corrupt. Starting fresh.")
    return set()

def save_downloaded_attachments(downloaded_set: set[str]):
    # ... (this function is unchanged)
    try:
        with open(DOWNLOADED_TRACKER_FILE, "w", encoding='utf-8') as f:
            json.dump(list(downloaded_set), f, indent=2)
    except IOError as e:
        logging.error(f"IOError saving downloaded attachments: {e}")

def generate_clean_filename(original_filename: str, message_content: str) -> str:
    # ... (this function is unchanged)
    suggested_title = ""
    if message_content:
        first_line = message_content.split('\n')[0]
        cleaned_title = re.sub(r'[*_`~>|]', '', first_line).strip()
        cleaned_title = re.sub(r'[^\w\s.-]', '', cleaned_title)
        cleaned_title = re.sub(r'\s+', '_', cleaned_title).strip('_')
        suggested_title = cleaned_title[:70] if cleaned_title else "no_title_content"
    
    if not suggested_title:
        suggested_title = os.path.splitext(original_filename)[0]
        suggested_title = re.sub(r'[^\w\s.-]', '', suggested_title)
        suggested_title = re.sub(r'\s+', '_', suggested_title).strip('_') or "unnamed_file"

    timestamp_prefix = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_suffix = random.randint(1000, 9999)
    file_extension = os.path.splitext(original_filename)[1] or ".mp4"
    
    return f"{suggested_title}_{timestamp_prefix}_{random_suffix}{file_extension}"

def build_metadata_to_save(attachment: dict, message_data: dict, final_filename: str, channel_id: str) -> dict:
    # ... (this function is unchanged)
    message_id = message_data.get("id", "unknown_id")
    guild_id = message_data.get("guild_id")
    discord_url = f"https://discord.com/channels/@me/{channel_id}/{message_id}" if not guild_id else f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

    return {
        "download_filename": final_filename,
        "message_id": message_id,
        "channel_id": channel_id,
        "author": message_data.get("author", {}),
        "timestamp": message_data.get("timestamp"),
        "prompt": message_data.get("content", ""),
        "original_attachment": attachment,
        "discord_message_url": discord_url,
    }

# --- HTML INDEX BUILDER (REWRITTEN FOR FOLDER SEARCH) ---

# In utils.py, replace the existing HTML generation functions

VIDEOS_PER_PAGE = 100

def _get_html_header(title: str) -> str:
    # The CSS for pagination has been updated
    return f"""
<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>{html.escape(title)}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --background-color: #f4f7f9;
            --card-background: #ffffff;
            --text-color: #333333;
            --heading-color: #1a202c;
            --accent-color: #4a90e2;
            --accent-color-hover: #357abd;
            --border-color: #e2e8f0;
            --shadow-color: rgba(0, 0, 0, 0.05);
        }}
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--background-color);
            color: var(--text-color);
            margin: 0;
            padding: 2rem;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-color);
        }}
        h1 {{
            color: var(--heading-color);
            font-weight: 700;
            font-size: 2.5rem;
        }}
        .filter-controls {{
            margin-bottom: 2.5rem;
            text-align: center;
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .filter-btn {{
            background-color: var(--card-background);
            color: var(--accent-color);
            border: 1px solid var(--accent-color);
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s ease-in-out;
        }}
        .filter-btn:hover {{
            background-color: var(--accent-color);
            color: white;
        }}
        .filter-btn.active {{
            background-color: var(--accent-color);
            color: white;
            box-shadow: 0 4px 14px rgba(74, 144, 226, 0.3);
        }}
        .video-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 2rem;
        }}
        .video-entry {{
            background: var(--card-background);
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px var(--shadow-color), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        }}
        .video-entry:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 15px -3px var(--shadow-color), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }}
        .video-entry.hidden {{
            display: none;
        }}
        video {{
            width: 100%;
            height: auto;
            background-color: #000;
            display: block;
        }}
        .video-info {{
            padding: 1.25rem;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
        }}
        h3 {{
            margin: 0 0 0.75rem 0;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--heading-color);
            line-height: 1.4;
        }}
        .prompt-content {{
            font-size: 0.9rem;
            background-color: var(--background-color);
            padding: 0.75rem;
            border-radius: 8px;
            white-space: pre-wrap;
            word-break: break-word;
            flex-grow: 1;
            margin-bottom: 1rem;
            border: 1px solid var(--border-color);
        }}
        .links {{
            font-size: 0.8rem;
            text-align: right;
        }}
        .links a {{
            color: var(--accent-color);
            text-decoration: none;
            margin-left: 1rem;
            font-weight: 500;
            transition: color 0.2s ease-in-out;
        }}
        .links a:hover {{
            color: var(--accent-color-hover);
            text-decoration: underline;
        }}
        .pagination {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 8px;
            margin: 3rem 0;
        }}
        .pagination a, .pagination span {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 40px;
            height: 40px;
            padding: 0 10px;
            border-radius: 8px;
            text-decoration: none;
            background-color: var(--card-background);
            color: var(--accent-color);
            border: 1px solid var(--border-color);
            font-weight: 500;
            transition: all 0.2s ease-in-out;
        }}
        .pagination a:hover {{
            background-color: var(--accent-color);
            color: white;
            border-color: var(--accent-color);
        }}
        .pagination .current-page {{
            background-color: var(--accent-color);
            color: white;
            border-color: var(--accent-color);
            font-weight: 700;
        }}
        .pagination .ellipsis {{
            border: none;
            background: none;
        }}
        footer {{
            text-align: center;
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border-color);
            color: #99aab5;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class='container'>
"""

def _get_html_footer() -> str:
    return """
    </div>
    <script>
        function filterVideos(category) {
            const allVideos = document.querySelectorAll('.video-entry');
            const buttons = document.querySelectorAll('.filter-btn');

            buttons.forEach(button => {
                if (button.getAttribute('data-filter') === category) {
                    button.classList.add('active');
                } else {
                    button.classList.remove('active');
                }
            });

            allVideos.forEach(video => {
                if (category === 'all' || video.getAttribute('data-category') === category) {
                    video.classList.remove('hidden');
                } else {
                    video.classList.add('hidden');
                }
            });
        }
        document.addEventListener('DOMContentLoaded', () => {
            filterVideos('all');
        });
    </script>
    <footer><p>&copy; 2025 Discord Scraper</p></footer>
</body>
</html>
"""

# <<< NEW: This function creates a smart, modern pagination control
def _get_pagination_nav(current_page: int, total_pages: int) -> str:
    """Creates a smart pagination navigation with ellipses."""
    if total_pages <= 1:
        return ""

    nav = "<div class='pagination'>"
    
    # Previous button
    if current_page > 1:
        nav += f"<a href='_page-{current_page - 1}.html'>&larr; Previous</a>"

    # Page numbers
    if total_pages <= 7: # Show all pages if 7 or fewer
        for i in range(1, total_pages + 1):
            nav += f"<a href='_page-{i}.html' class='{'current-page' if i == current_page else ''}'>{i}</a>"
    else:
        # Always show first page
        nav += f"<a href='_page-1.html' class='{'current-page' if 1 == current_page else ''}'>1</a>"
        
        # Ellipsis and pages around current page
        if current_page > 4:
            nav += "<span class='ellipsis'>...</span>"
        
        start = max(2, current_page - 2)
        end = min(total_pages - 1, current_page + 2)

        for i in range(start, end + 1):
            nav += f"<a href='_page-{i}.html' class='{'current-page' if i == current_page else ''}'>{i}</a>"
        
        if current_page < total_pages - 3:
            nav += "<span class='ellipsis'>...</span>"

        # Always show last page
        nav += f"<a href='_page-{total_pages}.html' class='{'current-page' if total_pages == current_page else ''}'>{total_pages}</a>"

    # Next button
    if current_page < total_pages:
        nav += f"<a href='_page-{current_page + 1}.html'>Next &rarr;</a>"
    
    nav += "</div>"
    return nav

def rebuild_html_index(download_dir: str):
    logging.info("Starting paginated HTML index rebuild from database...")
    if not os.path.exists(DATABASE_FILE):
        logging.warning(f"Database file '{DATABASE_FILE}' not found. Cannot build index.")
        return

    try:
        con = sqlite3.connect(DATABASE_FILE)
        con.row_factory = sqlite3.Row 
        cur = con.cursor()
        
        cur.execute("SELECT * FROM videos ORDER BY timestamp DESC")
        all_videos = cur.fetchall()
        con.close()

    except Exception as e:
        logging.error(f"Failed to read from database: {e}")
        return
        
    main_index_path = os.path.join(download_dir, "_index.html")

    if not all_videos:
        logging.info("No videos found in database to index.")
        with open(main_index_path, "w", encoding='utf-8') as f:
            f.write(_get_html_header("Video Index"))
            f.write("<header><h1>No Videos Found</h1><p>Start the scraper to download videos.</p></header>")
            f.write(_get_html_footer())
        return

    total_pages = math.ceil(len(all_videos) / VIDEOS_PER_PAGE)

    for page_num in range(1, total_pages + 1):
        page_path = os.path.join(download_dir, f"_page-{page_num}.html")
        start_index = (page_num - 1) * VIDEOS_PER_PAGE
        end_index = start_index + VIDEOS_PER_PAGE
        page_videos = all_videos[start_index:end_index]

        with open(page_path, "w", encoding='utf-8') as f:
            f.write(_get_html_header(f"Page {page_num} - Scraped Videos"))
            f.write(f"<header><h1>Scraped Videos</h1><p>A collection of all downloaded videos.</p></header>")
            
            f.write("""
            <div class='filter-controls'>
                <button class='filter-btn' data-filter='all' onclick="filterVideos('all')">All</button>
                <button class='filter-btn' data-filter='With_Audio' onclick="filterVideos('With_Audio')">With Audio</button>
                <button class='filter-btn' data-filter='Without_Audio' onclick="filterVideos('Without_Audio')">Without Audio</button>
                <button class='filter-btn' data-filter='Invalid_or_Corrupt' onclick="filterVideos('Invalid_or_Corrupt')">Corrupt</button>
            </div>
            """)

            f.write(_get_pagination_nav(page_num, total_pages))
            f.write("<div class='video-grid'>")

            for video_row in page_videos:
                original_filename = video_row["download_filename"]
                
                possible_subfolders = ["With_Audio", "Without_Audio", "Invalid_or_Corrupt", ""]
                
                found_path = None
                category = "Uncategorized"
                for folder in possible_subfolders:
                    test_path = os.path.join(download_dir, folder, original_filename)
                    if os.path.exists(test_path):
                        found_path = os.path.join(folder, original_filename).replace('\\', '/')
                        category = folder if folder else "Uncategorized"
                        break
                
                if not found_path:
                    logging.warning(f"Could not find file '{original_filename}'. Skipping from HTML index.")
                    continue

                prompt = video_row['prompt'] or 'No prompt available.'
                title = os.path.splitext(original_filename)[0].replace('_', ' ').title()
                discord_link = video_row['discord_message_url'] or '#'
                
                f.write(f"""
                <div class='video-entry' data-category='{category}'>
                    <video controls preload='metadata' src='{html.escape(found_path)}'></video>
                    <div class='video-info'>
                        <h3>{html.escape(title)}</h3>
                        <div class='prompt-content'>{html.escape(prompt)}</div>
                        <div class='links'>
                            <a href='{html.escape(found_path)}' download>Download</a>
                            <a href='{discord_link}' target='_blank'>Discord</a>
                        </div>
                    </div>
                </div>
                """)

            f.write("</div>")
            f.write(_get_pagination_nav(page_num, total_pages))
            f.write(_get_html_footer())
        logging.info(f"Generated _page-{page_num}.html with {len(page_videos)} videos.")
    
    # Main index page doesn't need pagination controls, just links to the pages
    with open(main_index_path, "w", encoding='utf-8') as f:
        f.write(_get_html_header("Video Index"))
        f.write(f"<header><h1>Video Page Index</h1><p>A total of {len(all_videos)} videos across {total_pages} pages.</p></header>")
        f.write(_get_pagination_nav(1, total_pages)) # Show the pagination for context
        f.write(_get_html_footer())
    
    logging.info("Main _index.html linking to all pages has been created.")