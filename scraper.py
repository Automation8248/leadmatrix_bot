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
    res = requests.post(url, json=payload)
    return res.status_code

def scrape_maps():
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Miami"]
    niches = ["Roofing", "Plumbing", "HVAC", "Cleaning Services"]
    query = f"{random.choice(niches)} in {random.choice(cities)}"
    
    print(f"Searching for: {query}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Google Maps search
        page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
        page.wait_for_timeout(5000)

        leads_found = 0
        # Sabhi potential business cards ko find karna
        results = page.query_selector_all('a.hfpxzc') 

        for res in results:
            if leads_found >= 2:
                break
            
            try:
                # Business par click karke details kholna
                res.click()
                page.wait_for_timeout(3000) # Sidebar load hone ka wait

                # --- WEBSITE CHECK LOGIC ---
                # Hum check kar rahe hain ki sidebar mein 'Website' link hai ya nahi
                website_exists = page.query_selector('a[aria-label*="website"]')
                
                if not website_exists:
                    # Agar website nahi hai, tabhi detail nikalenge
                    name = page.query_selector('h1.DUwDvf').inner_text() if page.query_selector('h1.DUwDvf') else "N/A"
                    phone = page.query_selector('button[data-item-id*="phone"]').inner_text() if page.query_selector('button[data-item-id*="phone"]') else "No Phone"
                    address = page.query_selector('button[data-item-id="address"]').inner_text() if page.query_selector('button[data-item-id="address"]') else "No Address"
                    map_url = page.url

                    # Telegram Message Layout
                    text = (
                        f"✅ *New Lead Found (No Website)*\n\n"
                        f"🏢 *Name:* {name}\n"
                        f"📞 *Phone:* {phone}\n"
                        f"📍 *Address:* {address}\n"
                        f"🌍 [Maps Link]({map_url})"
                    )

                    # Send to Telegram
                    status = send_telegram(text)
                    if status == 200:
                        print(f"Success: Sent {name}")
                        leads_found += 1
                    else:
                        print(f"Failed to send Telegram: {status}")
                
                else:
                    print("Skipping: Website already exists.")

            except Exception as e:
                print(f"Error processing lead: {e}")
                continue

        browser.close()

if __name__ == "__main__":
    scrape_maps()
