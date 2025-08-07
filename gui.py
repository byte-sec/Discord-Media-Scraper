# gui.py (Final Version with Channel Names)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import os
import logging
import re
import json

from config import DEFAULT_TOKEN, DOWNLOAD_DIR, PROXIES_FILE
from scraper_logic import ScraperLogic
from utils import load_proxies_from_file, save_proxies_to_file, load_downloaded_attachments

USER_SETTINGS_FILE = "user_settings.json"

class ScraperGUI:
    def __init__(self, master):
        self.master = master
        master.title("Discord Video Scraper")
        master.geometry("700x720")
        master.resizable(False, False)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#ECECEC')
        self.style.configure('TLabel', background='#ECECEC', foreground='#333', font=('Segoe UI', 10))
        self.style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=6)
        self.style.map('TButton', background=[('active', '#7289DA'), ('!disabled', '#6A7FC8')], foreground=[('active', 'white'), ('!disabled', 'white')])
        self.style.configure('TRadiobutton', background='#ECECEC', font=('Segoe UI', 10))
        self.style.configure('TEntry', padding=5, font=('Segoe UI', 10))
        self.style.configure('TCheckbutton', background='#ECECEC', font=('Segoe UI', 10))
        self.style.configure('Horizontal.TProgressbar', thickness=10)

        self.scraper_logic = None
        self.scraper_thread = None
        self.gui_queue = queue.Queue()
        self.is_closing = False
        
        # <<< NEW: This list will be the "source of truth" for channel data
        self.channel_data = []

        self.use_proxies_var = tk.BooleanVar()
        self.scan_mode_var = tk.StringVar(value=None)
        
        self._create_widgets()
        self._load_settings()
        self._check_queue()
        self.master.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.LabelFrame(main_frame, text="General Configuration", padding="10")
        top_frame.pack(fill=tk.X, pady=5)
        ttk.Label(top_frame, text="Discord User Token:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.token_entry = ttk.Entry(top_frame, width=60, show="*")
        self.token_entry.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        self.toggle_token_visibility_button = ttk.Button(top_frame, text="Show", command=self._toggle_token_visibility)
        self.toggle_token_visibility_button.grid(row=0, column=2, padx=5, pady=2)
        ttk.Label(top_frame, text="Download Directory:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.download_dir_entry = ttk.Entry(top_frame, width=60)
        self.download_dir_entry.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        ttk.Button(top_frame, text="Browse", command=self._browse_directory).grid(row=1, column=2, padx=5, pady=2)
        top_frame.columnconfigure(1, weight=1)

        channel_frame = ttk.LabelFrame(main_frame, text="Channel Management", padding="10")
        channel_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        channel_frame.columnconfigure(0, weight=1)
        channel_frame.columnconfigure(1, minsize=150)
        
        # <<< UPDATED: Add Channel section now has two input fields
        add_frame = ttk.Frame(channel_frame)
        add_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        add_frame.columnconfigure(1, weight=1)
        add_frame.columnconfigure(3, weight=1)
        
        ttk.Label(add_frame, text="Channel Name:").grid(row=0, column=0, padx=(0, 5), sticky='w')
        self.new_channel_name_entry = ttk.Entry(add_frame)
        self.new_channel_name_entry.grid(row=0, column=1, sticky='ew')
        
        ttk.Label(add_frame, text="Channel ID:").grid(row=0, column=2, padx=(10, 5), sticky='w')
        self.new_channel_id_entry = ttk.Entry(add_frame)
        self.new_channel_id_entry.grid(row=0, column=3, sticky='ew')
        
        self.add_channel_button = ttk.Button(add_frame, text="Add Channel", command=self._add_channel)
        self.add_channel_button.grid(row=0, column=4, padx=(5, 0))

        list_frame = ttk.Frame(channel_frame)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.channel_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        self.channel_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.channel_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.channel_listbox.config(yscrollcommand=scrollbar.set)
        self.channel_listbox.bind('<<ListboxSelect>>', self._on_channel_select)
        
        controls_frame = ttk.Frame(channel_frame)
        controls_frame.grid(row=1, column=1, sticky="ns", padx=(10, 0))
        self.remove_channel_button = ttk.Button(controls_frame, text="Remove Selected", command=self._remove_channel, state=tk.DISABLED)
        self.remove_channel_button.pack(fill=tk.X, pady=(0, 10))
        scan_mode_frame = ttk.LabelFrame(controls_frame, text="Scan Mode")
        scan_mode_frame.pack(fill=tk.X)
        new_only_rb = ttk.Radiobutton(scan_mode_frame, text="New Msgs Only", variable=self.scan_mode_var, value="new_only", command=self._update_selected_channel_mode, state=tk.DISABLED)
        new_only_rb.pack(anchor=tk.W)
        full_scan_rb = ttk.Radiobutton(scan_mode_frame, text="Full History Scan", variable=self.scan_mode_var, value="full_scan", command=self._update_selected_channel_mode, state=tk.DISABLED)
        full_scan_rb.pack(anchor=tk.W)
        channel_frame.rowconfigure(1, weight=1)

        proxy_frame = ttk.LabelFrame(main_frame, text="Proxy Settings", padding="10")
        proxy_frame.pack(pady=5, fill=tk.X)
        self.use_proxies_check = ttk.Checkbutton(proxy_frame, text="Use Proxies", variable=self.use_proxies_var, command=self._toggle_proxy_input)
        self.use_proxies_check.pack(anchor=tk.W)
        self.proxy_text = tk.Text(proxy_frame, height=4, font=('Consolas', 9))
        self.proxy_text.pack(pady=5, fill=tk.BOTH, expand=True)
        proxy_button_frame = ttk.Frame(proxy_frame)
        proxy_button_frame.pack(fill=tk.X)
        self.save_proxies_button = ttk.Button(proxy_button_frame, text="Save Proxies to File", command=self._save_proxies_to_file)
        self.save_proxies_button.pack(side=tk.LEFT, padx=(0,5))
        self.load_proxies_button = ttk.Button(proxy_button_frame, text="Load Proxies from File", command=self._load_proxies_from_file_manual)
        self.load_proxies_button.pack(side=tk.LEFT)

        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=5)
        self.save_settings_button = ttk.Button(bottom_frame, text="Save Settings", command=self._save_settings)
        self.save_settings_button.pack(side=tk.LEFT, padx=5)
        self.start_button = ttk.Button(bottom_frame, text="Start Scraper", command=self._start_scraper)
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.pause_button = ttk.Button(bottom_frame, text="Pause Scraper", command=self._pause_scraper, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.stop_button = ttk.Button(bottom_frame, text="Stop Scraper", command=self._stop_scraper, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        self.status_label = ttk.Label(main_frame, text="Status: Idle", font=('Segoe UI', 10, 'bold'))
        self.status_label.pack(fill=tk.X, padx=5)
        self.download_count_label = ttk.Label(main_frame, text="Total Downloaded: 0", font=('Segoe UI', 10, 'bold'))
        self.download_count_label.pack(fill=tk.X, padx=5)
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=100, mode="indeterminate")

    # <<< UPDATED: Logic now loads and populates the new channel_data list
    def _load_settings(self):
        settings = {}
        try:
            if os.path.exists(USER_SETTINGS_FILE):
                with open(USER_SETTINGS_FILE, 'r') as f: settings = json.load(f)
        except (IOError, json.JSONDecodeError) as e: logging.warning(f"Could not load user settings: {e}")

        self.token_entry.insert(0, DEFAULT_TOKEN)
        self.download_dir_entry.insert(0, settings.get('last_download_dir', DOWNLOAD_DIR))
        
        self.channel_data = settings.get('channels', [])
        self._refresh_channel_listbox() # Use a helper to populate the listbox
        
        self.use_proxies_var.set(settings.get('use_proxies', False))
        proxies_text = settings.get('last_proxies', '')
        if proxies_text:
            self.proxy_text.insert(tk.END, proxies_text)
        self._toggle_proxy_input()
        
        try:
            initial_downloads = load_downloaded_attachments()
            self.download_count_label.config(text=f"Total Downloaded: {len(initial_downloads)}")
        except Exception as e: logging.error(f"Could not load download count: {e}")

    # <<< UPDATED: Saves the new channel_data structure
    def _save_settings(self):
        settings = {
            'last_download_dir': self.download_dir_entry.get(),
            'channels': self.channel_data, # Save the list of dictionaries
            'use_proxies': self.use_proxies_var.get(),
            'last_proxies': self.proxy_text.get(1.0, tk.END).strip()
        }
        try:
            with open(USER_SETTINGS_FILE, 'w') as f: json.dump(settings, f, indent=4)
            self.status_label.config(text="Status: Settings Saved!")
        except IOError as e: logging.error(f"Could not save user settings: {e}")

    # <<< UPDATED: Gets channel IDs from the new data structure
    def _start_scraper(self):
        token = self.token_entry.get().strip()
        download_dir = self.download_dir_entry.get().strip()

        full_scan_channels = [ch['id'] for ch in self.channel_data if ch['mode'] == 'full_scan']
        new_only_channels = [ch['id'] for ch in self.channel_data if ch['mode'] == 'new_only']

        if not full_scan_channels and not new_only_channels:
            messagebox.showerror("Input Error", "Please add at least one channel to the list.")
            return

        # ... (rest of the function is the same)
        if self.scraper_thread and self.scraper_thread.is_alive():
            messagebox.showinfo("Scraper Status", "Scraper is already running.")
            return
        
        use_proxies = self.use_proxies_var.get()
        proxy_list = self.proxy_text.get(1.0, tk.END).strip().split('\n')
        
        self.scraper_logic = ScraperLogic(token, full_scan_channels, new_only_channels, download_dir, use_proxies, [p for p in proxy_list if p], self.gui_queue)
        self.scraper_thread = threading.Thread(target=self.scraper_logic.run, daemon=True)
        self.scraper_thread.start()

        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_bar.pack(fill=tk.X, pady=5)
        self.progress_bar.start()

    # <<< NEW HELPER: Refreshes the listbox based on the self.channel_data list
    def _refresh_channel_listbox(self):
        self.channel_listbox.delete(0, tk.END)
        for channel in self.channel_data:
            mode_text = 'Full Scan' if channel['mode'] == 'full_scan' else 'New Only'
            display_text = f"{channel['name']} ({mode_text})"
            self.channel_listbox.insert(tk.END, display_text)

    # <<< UPDATED: Now handles two input fields
    def _add_channel(self):
        new_id = self.new_channel_id_entry.get().strip()
        new_name = self.new_channel_name_entry.get().strip()

        if not new_name:
            messagebox.showerror("Invalid Name", "Channel Name cannot be empty.")
            return
        if not new_id.isdigit():
            messagebox.showerror("Invalid ID", "Channel ID must be a number.")
            return
        
        current_ids = [ch['id'] for ch in self.channel_data]
        if new_id in current_ids:
            messagebox.showwarning("Duplicate", "That Channel ID is already in the list.")
            return

        # Add the new channel as a dictionary
        self.channel_data.append({'name': new_name, 'id': new_id, 'mode': 'new_only'})
        self._refresh_channel_listbox()

        self.new_channel_id_entry.delete(0, tk.END)
        self.new_channel_name_entry.delete(0, tk.END)

    # <<< UPDATED: Removes from the data list first, then refreshes
    def _remove_channel(self):
        selected_indices = self.channel_listbox.curselection()
        if not selected_indices: return
        
        del self.channel_data[selected_indices[0]]
        self._refresh_channel_listbox()
        self._on_channel_select(None) # To reset the side panel

    # <<< UPDATED: Gets data from the list based on index, not string parsing
    def _on_channel_select(self, event):
        selected_indices = self.channel_listbox.curselection()
        is_selected = bool(selected_indices)
        
        self.remove_channel_button.config(state=tk.NORMAL if is_selected else tk.DISABLED)
        scan_mode_frame = self.remove_channel_button.master.winfo_children()[1]
        for grandchild in scan_mode_frame.winfo_children():
            grandchild.config(state=tk.NORMAL if is_selected else tk.DISABLED)
            
        if is_selected:
            selected_channel = self.channel_data[selected_indices[0]]
            self.scan_mode_var.set(selected_channel['mode'])

    # <<< UPDATED: Modifies the data list directly, then refreshes
    def _update_selected_channel_mode(self):
        selected_indices = self.channel_listbox.curselection()
        if not selected_indices: return
        
        idx = selected_indices[0]
        self.channel_data[idx]['mode'] = self.scan_mode_var.get()
        
        self._refresh_channel_listbox()
        self.channel_listbox.selection_set(idx)

    # --- Other functions (unchanged) ---
    def _on_closing(self):
        self._save_settings()
        if self.scraper_thread and self.scraper_thread.is_alive():
            if messagebox.askyesno("Exit", "Scraper is running. Are you sure you want to exit?"):
                self.is_closing = True
                self.status_label.config(text="Status: Shutting down...")
                if self.scraper_logic:
                    self.scraper_logic.stop_event.set()
                    self.scraper_logic.paused = False
            else: return
        else: self.master.destroy()

    def _check_queue(self):
        try:
            while True:
                message = self.gui_queue.get_nowait()
                if "status" in message and not self.is_closing:
                    self.status_label.config(text=f"Status: {message['status']}")
                if "count" in message:
                    self.download_count_label.config(text=f"Total Downloaded: {message['count']}")
                if message.get("status") == "Scraper Stopped.":
                    if self.is_closing: self.master.destroy()
                    else:
                        self.start_button.config(state=tk.NORMAL)
                        self.pause_button.config(state=tk.DISABLED, text="Pause Scraper")
                        self.stop_button.config(state=tk.DISABLED)
                        self.progress_bar.stop()
                        self.progress_bar.pack_forget()
        except queue.Empty: pass
        finally: self.master.after(100, self._check_queue)
    
    def _toggle_token_visibility(self): self.token_entry.config(show="" if self.token_entry.cget("show") == "*" else "*")
    
    def _browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.download_dir_entry.get())
        if directory:
            self.download_dir_entry.delete(0, tk.END)
            self.download_dir_entry.insert(0, directory)

    def _toggle_proxy_input(self):
        state = tk.NORMAL if self.use_proxies_var.get() else tk.DISABLED
        self.proxy_text.config(state=state)
        self.save_proxies_button.config(state=state)
        self.load_proxies_button.config(state=state)
        
    def _save_proxies_to_file(self):
        proxies_to_save = self.proxy_text.get(1.0, tk.END).strip().split('\n')
        save_proxies_to_file([p for p in proxies_to_save if p], PROXIES_FILE)
        messagebox.showinfo("Success", "Proxies saved to proxies.txt.")

    def _load_proxies_from_file_manual(self):
        proxies = load_proxies_from_file(PROXIES_FILE)
        self.proxy_text.delete(1.0, tk.END)
        for proxy in proxies: self.proxy_text.insert(tk.END, proxy + "\n")
        messagebox.showinfo("Success", f"Loaded {len(proxies)} proxies from proxies.txt.")

    def _pause_scraper(self):
        if self.scraper_logic and self.scraper_thread.is_alive():
            self.scraper_logic.paused = not self.scraper_logic.paused
            self.pause_button.config(text="Resume" if self.scraper_logic.paused else "Pause Scraper")
            self.status_label.config(text=f"Status: Scraper {'Paused' if self.scraper_logic.paused else 'Resuming...'}")
            if self.scraper_logic.paused: self.progress_bar.stop()
            else: self.progress_bar.start()

    def _stop_scraper(self):
        if self.scraper_logic:
            self.scraper_logic.stop_event.set()
            self.scraper_logic.paused = False
            self.status_label.config(text="Status: Stopping Scraper...")