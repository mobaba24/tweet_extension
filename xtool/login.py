"""One-time login. Opens Chromium with the persistent profile so you can log
into X; the session is saved for scrape runs. Run once (or whenever logged out):

    python login.py
"""
from playwright.sync_api import sync_playwright
import config

config.PROFILE_DIR.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(config.PROFILE_DIR),
        headless=False,
        viewport={"width": 1280, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://x.com/login")
    input("Log into X in the browser window, then press Enter here to save the session and exit...")
    ctx.close()
    print("Session saved to", config.PROFILE_DIR)
