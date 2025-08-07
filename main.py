# main.py (Final Version)
import tkinter as tk
from gui import ScraperGUI
import logging
import os
from config import DEFAULT_TOKEN, PROXIES_FILE, DOWNLOADED_TRACKER_FILE, DEFAULT_PROXY_LIST
from utils import save_proxies_to_file, save_downloaded_attachments, init_database # <<< ADD init_database

# Configure logging for the entire application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Main function to initialize and run the Discord Scraper GUI application."""
    logging.info("Starting Discord Video Scraper application...")

    # <<< NEW: Initialize the SQLite database on startup
    try:
        init_database()
    except Exception as e:
        logging.critical(f"COULD NOT INITIALIZE DATABASE. The application may not work correctly. Error: {e}")
    
    # --- Immediate File Creation / Initialization ---
    try:
        if not os.path.exists(PROXIES_FILE):
            save_proxies_to_file(DEFAULT_PROXY_LIST if DEFAULT_PROXY_LIST else [])
            logging.info(f"Created '{PROXIES_FILE}' with {'default' if DEFAULT_PROXY_LIST else 'empty'} content.")
        else:
            logging.info(f"'{PROXIES_FILE}' already exists.")
    except Exception as e:
        logging.error(f"Failed to ensure '{PROXIES_FILE}' exists or is initialized: {e}")

    try:
        if not os.path.exists(DOWNLOADED_TRACKER_FILE):
            save_downloaded_attachments(set())
            logging.info(f"Created empty '{DOWNLOADED_TRACKER_FILE}'.")
        else:
            logging.info(f"'{DOWNLOADED_TRACKER_FILE}' already exists.")
    except Exception as e:
        logging.error(f"Failed to ensure '{DOWNLOADED_TRACKER_FILE}' exists or is initialized: {e}")
    
    if not DEFAULT_TOKEN:
        logging.warning("Discord TOKEN is empty. Please update config.py or enter it in the GUI.")
        print("\n=======================================================")
        print("WARNING: Discord TOKEN is currently empty. ")
        print("Please set the 'DISCORD_USER_TOKEN' environment variable or paste your token into the GUI.")
        print("=======================================================\n")

    root = tk.Tk()
    app = ScraperGUI(root)
    root.mainloop()
    logging.info("Scraper GUI closed. Application exiting.")

if __name__ == "__main__":
    main()