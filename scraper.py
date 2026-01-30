import time
import random
import json
import os
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import date

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Topics aur Places ki list
CITIES = ["New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Miami, FL", "Las Vegas, NV"]
TOPICS = ["Salon", "Plumber", "Dentist", "Auto Repair", "Real Estate Agency", "Gym", "Florist", "Electrician"]

def send_telegram(topic, lead):
    msg = (
        f"🟦 *{topic.upper()} LEAD* 🇺🇸\n\n"
        f"🏪 *Name:* {lead['Name']}\n"
        f"📞 *Phone:* `{lead['Phone']}`\n"
        f"🌐 *Web:* {lead['WebsiteStatus']}\n"
        f"⭐ *Rating:* {lead['Rating']} ({lead['Reviews']})\n"
        f"📍 *Addr:* {lead['Address']}\n"
        f"🔗 [Maps Link]({lead['MapLink']})"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(url, json=payload)

def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)
    return driver

def run_scraper():
    driver = get_driver()
    
    # 1. Random Selection
    city = random.choice(CITIES)
    topic = random.choice(TOPICS)
    query = f"{topic} in {city}"
    print(f"🔎 Searching: {query}")

    driver.get(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
    time.sleep(5)

    # 2. History Load
    if os.path.exists('history.json'):
        with open('history.json', 'r') as f: history = json.load(f)
    else: history = []

    leads_found = []

    # 3. Scroll Feed (To load more results)
    try:
        feed = driver.find_element(By.CSS_SELECTOR, "div[role='feed']")
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
        time.sleep(3)
    except: pass

    # 4. Find Listings (Using generic selector)
    # Class 'hfpxzc' is often the clickable link for businesses on Maps
    listings = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")[:10]

    for listing in listings:
        try:
            # Click the listing to open details
            listing.click()
            time.sleep(random.uniform(2, 4))
            
            # Scrape Details from the Side Panel
            name = driver.find_element(By.TAG_NAME, "h1").text
            
            if name in history: continue

            try:
                phone = driver.find_element(By.CSS_SELECTOR, "button[data-item-id^='phone:']").get_attribute("aria-label").replace("Phone: ", "")
            except: phone = "Not Listed"

            try:
                website_btn = driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority']")
                website = website_btn.get_attribute("href")
            except: website = ""

            try:
                rating_text = driver.find_element(By.CSS_SELECTOR, "div.F7nice").text
                rating = rating_text.split("\n")[0]
                reviews = rating_text.split("\n")[1]
            except: 
                rating = "0"
                reviews = "(0)"

            # 5. GOLD FILTER (Website Missing or Weak)
            is_gold = False
            status = "✅ Active"
            
            if not website:
                is_gold = True
                status = "❌ No Website (GOLD)"
            elif "facebook.com" in website or "wix.com" in website:
                is_gold = True
                status = "⚠️ Weak Website"

            # Check reviews count (Clean string first)
            review_count = int(''.join(filter(str.isdigit, reviews))) if any(c.isdigit() for c in reviews) else 0

            if is_gold and review_count >= 10:
                lead = {
                    "Name": name,
                    "Phone": phone,
                    "WebsiteStatus": status,
                    "Rating": rating,
                    "Reviews": reviews,
                    "Address": city,
                    "MapLink": driver.current_url
                }
                
                send_telegram(topic, lead)
                leads_found.append(lead)
                history.append(name)
                print(f"🚀 Sent: {name}")
        
        except Exception as e:
            # print(e)
            continue

    driver.quit()

    # Save Data
    with open('history.json', 'w') as f: json.dump(history, f)
    
    if leads_found:
        df = pd.DataFrame(leads_found)
        # Append mode to keep previous leads
        df.to_csv('leads.csv', mode='a', index=False, header=not os.path.exists('leads.csv'))

if __name__ == "__main__":
    run_scraper()
