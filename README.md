# Discord-Media-Scraper - A Professional Discord Media Scraper

![Vortex Scraper GUI](https://i.imgur.com/your-gui-screenshot.png) 
*(Suggestion: Take a screenshot of your GUI, upload it to a site like [imgur.com](https://imgur.com), and paste the link here)*

Vortex is a powerful and robust GUI-based scraper for downloading and automatically organizing videos from Discord channels. Built with Python and Tkinter, it provides a user-friendly interface to manage complex scraping tasks, complete with advanced features like intelligent proxy rotation, self-healing proxy lists, and a fast, scalable SQLite backend.

---
## ✨ Key Features

* **User-Friendly GUI:** A simple interface built with Tkinter to manage channels, settings, and monitor progress.
* **Advanced Proxy Management:**
    * Sequential proxy rotation with failover.
    * Differentiates between dead proxies (immediate removal) and slow proxies (5-try rule).
    * The cleaned list of working proxies is automatically saved to `proxies.txt`.
* **Efficient & Resumable Scans:**
    * Uses a "Dual-Ended" scanning method to quickly fetch new videos while efficiently backfilling a channel's history.
    * Automatically marks channels as "complete" to prevent re-scanning.
* **Scalable Backend:**
    * All video metadata is stored in a fast and efficient **SQLite database**.
    * Includes a one-time script to migrate old JSON metadata to the new database.
* **Automatic Categorization:**
    * After downloading, videos are automatically checked and sorted into folders based on whether they contain audio (`With_Audio`, `Without_Audio`) or are corrupt (`Invalid_or_Corrupt`).
* **Beautiful HTML Gallery:**
    * Automatically generates a modern, paginated HTML index of all downloaded videos.
    * Features interactive buttons to filter the gallery by category.

---
## 🚀 Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/Vortex.git](https://github.com/your-username/Vortex.git)
    cd Vortex
    ```

2.  **Install dependencies:**
    This project requires Python 3. Create a `requirements.txt` file (see below) and run:
    ```bash
    python -m pip install -r requirements.txt
    ```

---
## 📋 How to Use

1.  **Configuration:** Open the `config.py` file and add your Discord user token and set your desired download directory.
2.  **Add Proxies:** Add your list of proxies to the `proxies.txt` file (one per line).
3.  **Run the Application:**
    ```bash
    python main.py
    ```
4.  **Add Channels:** In the GUI, add channels using their custom name and numeric ID.
5.  **Start Scraping:** Click the "Start Scraper" button to begin.

---
## `requirements.txt`

For the installation to work, create a file named **`requirements.txt`** in your project folder and add the following lines to it.

```
requests
moviepy
```
