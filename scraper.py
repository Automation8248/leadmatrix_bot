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
from datetime import date

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 1. Target Locations (USA Major Cities)
CITIES = [
    "Houston, TX", "Los Angeles, CA", "Miami, FL", "Chicago, IL", 
    "Phoenix, AZ", "Dallas, TX", "Atlanta, GA", "Denver, CO", 
    "Seattle, WA", "Las Vegas, NV", "Orlando, FL", "Austin, TX"
]

# 2. Master Category List (Top 5 Priority First)
CATEGORIES = [
    # --- 🔥 TOP 5 (High Conversion) ---
    "Salon", "Auto Repair Shop", "Restaurant", "Dental Clinic", "Grocery Store",
    
    # --- 🏪 Retail ---
    "Liquor Store", "Bakery", "Furniture Store", "Boutique", "Jewelry Store", "Florist",
    
    # --- 🏠 Home Services ---
    "Plumber", "Electrician", "HVAC Repair", "Landscaping Service", "Roofing Service",
    
    # --- 🏗️ Construction ---
    "General Contractor", "Interior Designer", "Real Estate Agency",
    
    # --- 💇 Beauty & Wellness ---
    "Barber Shop", "Spa", "Gym", "Nail Salon", "Massage Therapist",
    
    # --- ⚖️ Professional ---
    "Law Firm", "Accountant", "Insurance Agency"
]

def send_telegram(category, lead):
    # Telegram Format: CLEAN CARD with BOLD HEADING
    msg = (
        f"🟦 *{category.upper()}* 🇺🇸\n\n"
        f"🏪 *Business:* {lead['Name']}\n"
        f"📞 *Phone:* `{lead['Phone']}`\n"
        f"📧 *Email:* `{lead['Email']}`\n"
        f"📍 *Location:* {lead['Address']}\n"
        f"🌐 *Website:* {lead['WebsiteStatus']}\n"
        f"⭐ *Rating:* {lead['Rating']} ({lead['Reviews']} reviews)\n"
        f"🔗 [Google Maps Link]({lead['MapLink']})\n\n"
        f"📅 *Scraped:* {date.today()}"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID, 
        "text": msg, 
        "parse_mode": "Markdown", 
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

def get_stealth_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    return driver

def run_scraper():
    driver = get_stealth_driver()
    
    # Randomly pick 1 City and 1 Category to keep it natural
    target_city = random.choice(CITIES)
    target_category = random.choice(CATEGORIES)
    search_query = f"{target_category} in {target_city}"
    
    print(f"🚀 Searching: {search_query}...")
    
    # Google Maps Search URL
    driver.get(f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}/")
    time.sleep(random.uniform(4, 7))

    # Load History
    if os.path.exists('history.json'):
        with open('history.json', 'r') as f: history = json.load(f)
    else: history = []

    leads_found = []

    # 🖱️ Scroll mimics Human behavior
    print("👀 Scrolling to find businesses...")
    for _ in range(3):
        try:
            scrollable_div = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(random.uniform(2, 4))
        except:
            pass # Sometimes feed isn't immediately found

    # Extract Elements (Generic Selector for Cards)
    # Note: Selectors like Nv2Ybe can change. Using generic class structure.
    items = driver.find_elements(By.CSS_SELECTOR, "div[role='article']")[:12] # Limit to 12 per run for safety

    for item in items:
        try:
            # Basic Data Extraction
            name = item.get_attribute("aria-label")
            if not name or name in history: continue

            # Click to open details
            item.click()
            time.sleep(random.uniform(2, 4))

            # Extract Phone & Website
            try:
                phone_elem = driver.find_element(By.CSS_SELECTOR, "button[data-item-id^='phone:']")
                phone = phone_elem.get_attribute("aria-label").replace("Phone: ", "")
            except: phone = "Not Listed"

            try:
                web_elem = driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority']")
                website = web_elem.get_attribute("href")
            except: website = ""

            try:
                rating_text = item.find_element(By.CSS_SELECTOR, "span[role='img']").get_attribute("aria-label")
                # Format: "4.5 stars 50 reviews"
                rating = rating_text.split(" ")[0]
                reviews = int(rating_text.split("(")[1].split(")")[0].replace(",",""))
            except: 
                rating = "N/A"
                reviews = 0

            # --- 🧠 SMART FILTER LOGIC ---
            is_gold_lead = False
            website_status = "🌐 Active"

            # Condition 1: No Website OR "Bad" Website (FB, Wix, Site.google)
            bad_domains = ['facebook.com', 'wix.com', 'business.site', 'wordpress.com']
            if not website:
                is_gold_lead = True
                website_status = "❌ No Website (GOLD)"
            elif any(domain in website for domain in bad_domains):
                is_gold_lead = True
                website_status = f"⚠️ Weak ({website})"

            # Condition 2: Reviews >= 20 (Established Business)
            if is_gold_lead and reviews >= 20:
                lead_data = {
                    "Name": name,
                    "Phone": phone,
                    "Email": "Not Found (Manual Check Required)", # Maps rarely has email
                    "Address": target_city,
                    "WebsiteStatus": website_status,
                    "Rating": rating,
                    "Reviews": reviews,
                    "MapLink": driver.current_url
                }
                
                send_telegram(target_category, lead_data)
                leads_found.append(lead_data)
                history.append(name)
                print(f"✅ Lead Sent: {name}")
                time.sleep(random.uniform(5, 10)) # Delay between sends

        except Exception as e:
            # print(f"Skipping item due to: {e}") 
            continue

    # Save Data
    with open('history.json', 'w') as f: json.dump(history, f)
    
    if leads_found:
        df = pd.DataFrame(leads_found)
        df.to_csv('leads.csv', mode='a', index=False, header=not os.path.exists('leads.csv'))

    driver.quit()

if __name__ == "__main__":
    run_scraper()
