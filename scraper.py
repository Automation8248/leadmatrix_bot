import os
import time
import random
import requests
from playwright.sync_api import sync_playwright

# Configuration
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def scrape_maps():
    # USA Target Locations & Niches
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Miami", "Dallas"]
    niches = ["Roofing Contractors", "Plumbing Services", "HVAC Repair", "Landscaping"]
    
    query = f"{random.choice(niches)} in {random.choice(cities)}"
    print(f"Searching for: {query}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Real user browser simulate karne ke liye
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        page = context.new_page()
        
        # Google Maps URL
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        page.goto(search_url)
        page.wait_for_timeout(5000) # Wait for results to load

        leads_found = 0
        # Maps par results ke containers
        items = page.query_selector_all('div[role="article"]')

        for item in items:
            if leads_found >= 2: # Daily Limit 2 Leads
                break

            # Logic: Website button agar nahi hai
            website_btn = item.query_selector('a[aria-label*="website"]')
            
            if not website_btn:
                try:
                    # Lead Details
                    name_el = item.query_selector('.qBF1Pd')
                    name = name_el.inner_text() if name_el else "Unknown Business"
                    
                    item.click() # Click to open details sidebar
                    page.wait_for_timeout(3000)
                    
                    # Scrape Details from Sidebar
                    address = page.query_selector('button[data-item-id="address"]').inner_text() if page.query_selector('button[data-item-id="address"]') else "Address not found"
                    phone = page.query_selector('button[data-item-id*="phone"]').inner_text() if page.query_selector('button[data-item-id*="phone"]') else "No Phone"
                    map_url = page.url

                    message = (
                        f"🔥 *New USA Lead (No Website)*\n\n"
                        f"🏢 *Name:* {name}\n"
                        f"📞 *Phone:* {phone}\n"
                        f"📍 *Address:* {address}\n"
                        f"🌍 [Open in Maps]({map_url})"
                    )
                    
                    send_telegram(message)
                    leads_found += 1
                except Exception as e:
                    print(f"Error skipping one item: {e}")
                    continue

        browser.close()

if __name__ == "__main__":
    scrape_maps()
