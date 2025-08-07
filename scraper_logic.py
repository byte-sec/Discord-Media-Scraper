import os
import json
import time
import random
import threading
import requests
import logging
import queue
import shutil 
from moviepy import VideoFileClip

from config import *
from utils import (
    load_downloaded_attachments, save_downloaded_attachments,
    generate_clean_filename, build_metadata_to_save,
    rebuild_html_index,
    save_metadata_to_db,
    save_proxies_to_file 
)
from config import USER_AGENT_LIST

class ScraperLogic:
    def __init__(self, token: str, full_scan_channels: list[str], new_only_channels: list[str], download_dir: str, use_proxies: bool, proxy_list: list[str], gui_queue: queue.Queue):
        self.token = token
        self.download_dir = download_dir
        self.use_proxies = use_proxies
        self.initial_proxy_list = proxy_list
        self.gui_queue = gui_queue
        
        self.channels_to_scan = {}
        for cid in full_scan_channels: self.channels_to_scan[cid] = 'full_scan'
        for cid in new_only_channels: self.channels_to_scan[cid] = 'new_only'
        
        self.paused = False
        self.stop_event = threading.Event()
        
        self.running_proxies = list(self.initial_proxy_list)
        self.proxy_index = 0
        
        self.proxy_failure_counts = {proxy: 0 for proxy in self.running_proxies}
        
        self.session = requests.Session()
        self.session.headers.update({"Authorization": self.token, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
        
        self.downloaded_attachments = load_downloaded_attachments()
        self.download_count = len(self.downloaded_attachments)
        self.scraper_state = self._load_state()
        # This line is no longer necessary as the metadata folder is deprecated, but leaving it does no harm.
        os.makedirs(os.path.join(self.download_dir, "metadata"), exist_ok=True)
        self._update_gui_status("Idle")

    def _load_state(self) -> dict:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f: return json.load(f)
            except json.JSONDecodeError: return {}
        return {}

    def _save_state(self):
        try:
            with open(STATE_FILE, 'w') as f: json.dump(self.scraper_state, f, indent=2)
        except Exception as e: logging.error(f"Could not save scraper state: {e}")

    def _update_gui_status(self, status_text: str):
        self.gui_queue.put({"status": status_text, "count": self.download_count})

    def _execute_request_with_failover(self, url: str, **kwargs):
        if not self.use_proxies or not self.running_proxies:
            try:
                headers = {'User-Agent': random.choice(USER_AGENT_LIST)}
                response = self.session.get(url, headers=headers, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logging.error(f"Direct request to {url} failed: {e}")
                return None

        attempts = 0
        max_attempts = len(self.running_proxies)
        while attempts < max_attempts and self.running_proxies:
            if self.stop_event.is_set(): return None

            self.proxy_index %= len(self.running_proxies)
            current_proxy_url = self.running_proxies[self.proxy_index]
            proxies = {"http": current_proxy_url, "https": current_proxy_url}
            
            try:
                logging.info(f"Attempting request via proxy {current_proxy_url} ({self.proxy_index + 1}/{len(self.running_proxies)})")
                headers = {'User-Agent': random.choice(USER_AGENT_LIST)}
                response = self.session.get(url, headers=headers, proxies=proxies, **kwargs)
                response.raise_for_status()
                
                if self.proxy_failure_counts.get(current_proxy_url, 0) > 0:
                    logging.info(f"Proxy {current_proxy_url} succeeded. Resetting failure count.")
                    self.proxy_failure_counts[current_proxy_url] = 0
                
                self.proxy_index = (self.proxy_index + 1) % len(self.running_proxies)
                return response

            except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
                logging.error(f"Proxy {current_proxy_url} is dead (Connection/Proxy Error). Removing immediately. Reason: {e}")
                self._update_gui_status(f"Dead proxy removed: {current_proxy_url}")
                
                self.running_proxies.pop(self.proxy_index)
                if current_proxy_url in self.proxy_failure_counts:
                    del self.proxy_failure_counts[current_proxy_url]

                save_proxies_to_file(self.running_proxies)
                
                max_attempts = len(self.running_proxies)
                attempts = 0
                continue 

            except requests.exceptions.Timeout as e:
                logging.warning(f"Proxy {current_proxy_url} timed out. Applying 5-try rule. Reason: {e}")
                
                self.proxy_failure_counts[current_proxy_url] = self.proxy_failure_counts.get(current_proxy_url, 0) + 1
                failure_count = self.proxy_failure_counts[current_proxy_url]
                logging.warning(f"Proxy {current_proxy_url} has {failure_count}/5 consecutive soft failures.")

                if failure_count >= 5:
                    logging.error(f"Proxy {current_proxy_url} has failed 5 times. Removing it from the list.")
                    self._update_gui_status(f"Removing slow proxy: {current_proxy_url}")
                    
                    self.running_proxies.pop(self.proxy_index)
                    del self.proxy_failure_counts[current_proxy_url]

                    save_proxies_to_file(self.running_proxies)
                    
                    max_attempts = len(self.running_proxies)
                    attempts = 0
                else:
                    # This check prevents an error if the last proxy is removed
                    if self.running_proxies:
                        self.proxy_index = (self.proxy_index + 1) % len(self.running_proxies)
            
            attempts += 1

        logging.error(f"All proxies failed for the request to {url}.")
        self._update_gui_status("All proxies failed. Check console/logs.")
        return None

    def run(self):
        rebuild_html_index(self.download_dir)
        self._update_gui_status("Scraper Started.")
        
        while not self.stop_event.is_set():
            if self.paused:
                self.stop_event.wait(2)
                continue
            
            channel_list = list(self.channels_to_scan.keys())
            random.shuffle(channel_list)
            
            for channel_id in channel_list:
                if self.stop_event.is_set(): break
                self._process_channel(channel_id)
                
                if not self.stop_event.is_set():
                    inter_channel_delay = random.uniform(5, 15)
                    self.stop_event.wait(inter_channel_delay)

            if self.stop_event.is_set(): break
            
            long_sleep_duration = random.uniform(SLEEP_AFTER_NO_MESSAGES - 60, SLEEP_AFTER_NO_MESSAGES + 60)
            self._update_gui_status(f"Cycle complete. Waiting for ~{int(long_sleep_duration / 60)} minutes...")
            self.stop_event.wait(long_sleep_duration)

        self._update_gui_status("Scraper Stopped.")
        
    def _process_messages(self, messages: list, channel_id: str):
        if not messages:
            return 0
            
        found_count = 0
        for msg in messages:
            if self.stop_event.is_set(): break
            for attachment in msg.get("attachments", []):
                if attachment.get("content_type", "").startswith("video/"):
                    unique_id = f"{msg['id']}-{attachment['id']}"
                    if unique_id not in self.downloaded_attachments:
                        self._download_file(attachment, msg, channel_id)
                        found_count += 1
        return found_count

    def _process_channel(self, channel_id: str):
        scan_mode = self.channels_to_scan[channel_id]
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
        
        self._update_gui_status(f"Checking for new messages in {channel_id}...")
        after_id = self.scraper_state.get(f"{channel_id}_after")
        params = {'limit': MESSAGES_LIMIT}
        if after_id:
            params['after'] = after_id

        response = self._execute_request_with_failover(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        if response:
            messages = response.json()
            if messages:
                messages.reverse()
                self._process_messages(messages, channel_id)
                self.scraper_state[f"{channel_id}_after"] = messages[-1]['id']
                self._save_state()

        if self.stop_event.is_set(): return

        history_complete_key = f"{channel_id}_history_complete"
        if scan_mode == 'full_scan' and not self.scraper_state.get(history_complete_key, False):
            self._update_gui_status(f"Backfilling history for {channel_id}...")
            # Make sure params are reset for the 'before' call
            params = {'limit': MESSAGES_LIMIT}
            before_id = self.scraper_state.get(f"{channel_id}_before")
            if before_id:
                params['before'] = before_id

            response = self._execute_request_with_failover(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            if response:
                messages = response.json()
                if messages:
                    self._process_messages(messages, channel_id)
                    self.scraper_state[f"{channel_id}_before"] = messages[-1]['id']
                    self._save_state()
                else:
                    logging.info(f"Reached the beginning of history for channel {channel_id}. Marking as complete.")
                    self._update_gui_status(f"History scan for {channel_id} is complete!")
                    self.scraper_state[history_complete_key] = True
                    self._save_state()

    def _download_file(self, attachment: dict, message_data: dict, channel_id: str):
        unique_id = f"{message_data['id']}-{attachment['id']}"
        if unique_id in self.downloaded_attachments: return

        final_filename = generate_clean_filename(attachment.get("filename"), message_data.get("content", ""))
        filepath = os.path.join(self.download_dir, final_filename)
        
        try:
            r = self._execute_request_with_failover(attachment["url"], stream=True, timeout=REQUEST_TIMEOUT_SECONDS)

            if not r:
                logging.error(f"Download failed for {attachment.get('filename')} after trying all proxies.")
                return

            with r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if self.stop_event.is_set():
                            logging.info(f"Download of {final_filename} cancelled by stop signal.")
                            if os.path.exists(filepath):
                                os.remove(filepath)
                            return
                        f.write(chunk)
            
            metadata = build_metadata_to_save(attachment, message_data, final_filename, channel_id)
            save_metadata_to_db(metadata)

            self.downloaded_attachments.add(unique_id)
            self.download_count += 1
            save_downloaded_attachments(self.downloaded_attachments)
            rebuild_html_index(self.download_dir)
            self._update_gui_status(f"Downloaded: {final_filename}")

            # --- Post-processing: Categorize by Audio ---
            try:
                # Use 'filepath' which is the known location of the downloaded file
                video_path = filepath
                
                with VideoFileClip(video_path) as clip:
                    has_audio = clip.audio is not None

                if has_audio:
                    category_folder = "With_Audio"
                else:
                    category_folder = "Without_Audio"
                
                target_dir = os.path.join(self.download_dir, category_folder)
                os.makedirs(target_dir, exist_ok=True)
                
                new_video_path = os.path.join(target_dir, final_filename)
                shutil.move(video_path, new_video_path)
                
                logging.info(f"Moved '{final_filename}' to '{category_folder}' folder.")
                self._update_gui_status(f"Categorized: {final_filename}")
            
            except Exception as e:
                logging.error(f"Could not categorize video {final_filename}. Error: {e}")

        except Exception as e:
            logging.error(f"Failed to download {attachment.get('filename')}: {e}")
            if os.path.exists(filepath): 
                os.remove(filepath)