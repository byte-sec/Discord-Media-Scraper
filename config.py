# config.py

import os

# === USER CONFIGURATION ===
# IMPORTANT:
# 1. DO NOT HARDCODE YOUR DISCORD USER TOKEN HERE FOR SECURITY REASONS.
#    Instead, use environment variables.
#    Example: DEFAULT_TOKEN = os.getenv("DISCORD_USER_TOKEN", "")
# 2. If left empty (""), you MUST enter your token manually in the GUI every time.
# 3. For production, ALWAYS use environment variables.
# DEFAULT_TOKEN = "YOUR_ACTUAL_DISCORD_TOKEN_GOES_HERE_LIKE_THIS" # Original placeholder
DEFAULT_TOKEN = "DISCORD_TOKEN_HERE" # Per your request, this is unchanged.

# You can now enter one or more Channel IDs, separated by a comma.
DEFAULT_CHANNEL_ID = "CHANNEL_ID_1, CHANNEL_ID_2" # <--- REPLACE THIS WITH YOUR DESIRED CHANNEL IDs

# Default download directory
# Using a relative path is more portable across different computers.
# This will create a 'discord_downloads' folder in the same directory as the script.
#DOWNLOAD_DIR = r"F:\prompt results\discord"
DOWNLOAD_DIR = "DOWNLOAD_PATH"

# File names for persistent data
PROXIES_FILE = "proxies.txt"
DOWNLOADED_TRACKER_FILE = "downloaded_attachments.json"
STATE_FILE = "scraper_state.json"


# === API CONSTANTS ===
DISCORD_API_BASE = "https://discord.com/api/v9"
MESSAGES_LIMIT = 100 # Max messages per API call

# === TIMEOUTS & RETRIES ===
REQUEST_TIMEOUT_SECONDS = 10 # General request timeout for HTTP requests
RETRY_AFTER_DEFAULT = 5 # Default seconds to wait if Retry-After header is missing (Discord API)
SLEEP_AFTER_NO_MESSAGES = 300 # Seconds to sleep when no new messages are found (5 minutes)
POLITE_API_DELAY_MIN = 1 # Minimum seconds to wait between API calls
POLITE_API_DELAY_MAX = 3 # Maximum seconds to wait between API calls

# === PROXY LIST (Example - will be overridden by proxies.txt or GUI input) ===
# It's recommended to periodically test and update your proxy list for reliability.
# These are just examples and are unlikely to be reliable.
DEFAULT_PROXY_LIST = [
    "http://13.57.11.118:3128", "http://209.97.181.142:5353", "http://8.222.17.214:1080",
    "http://188.166.197.129:3128", "http://193.151.141.17:8080", "http://8.219.97.248:80",
    "http://195.158.8.123:3128", "http://3.27.237.252:3128", "http://105.225.53.124:3128",
    "http://147.75.34.74:10019", "http://63.177.10.110:3128", "http://89.117.145.245:3128",
    "http://60.249.94.59:3128", "http://18.170.63.85:999", "http://177.253.195.107:999",
    "http://18.132.14.119:3128", "http://202.58.77.7:7777", "http://102.222.161.143:3128",
    "http://4.149.210.210:3128", "http://43.217.134.23:3128", "http://3.147.53.66:80",
    "http://13.212.216.15:52638", "http://18.100.217.180:3128", "http://13.38.66.165:3128",
    "http://13.221.134.55:3128", "http://91.213.99.134:3128", "http://98.130.47.34:3128",
    "http://18.101.7.10:3128", "http://43.199.163.10:3128"
]

# === USER AGENTS ===
# A list of user-agent strings to rotate through. This makes requests
# appear as if they are coming from different browsers, reducing block chance.
USER_AGENT_LIST = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0"

]
