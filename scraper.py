import time
import random
import json
import os
import requests
import pandas as pd
from datetime import date
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
from selenium.webdriver.common.by import By

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Goal per run (Kitni leads milne par rukna hai)
TARGET_LEADS = 8
# Max cities to check if leads not found
MAX_ATTEMPTS = 20

# 🌍 DOLLAR LOCATIONS (USA, Canada, Australia)
LOCATIONS = [
    # USA (Top Cities)
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ",
    "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", "Dallas, TX", "San Jose, CA",
    "Austin, TX", "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH", "Charlotte, NC",
    "San Francisco, CA", "Indianapolis, IN", "Seattle, WA", "Denver, CO", "Washington, DC",
    "Boston, MA", "El Paso, TX", "Nashville, TN", "Detroit, MI", "Portland, OR",
    "Las Vegas, NV", "Memphis, TN", "Louisville, KY", "Baltimore, MD", "Milwaukee, WI",
    "Albuquerque, NM", "Tucson, AZ", "Fresno, CA", "Mesa, AZ", "Atlanta, GA",
    "Sacramento, CA", "Kansas City, MO", "Miami, FL", "Raleigh, NC", "Omaha, NE",
    # Canada
    "Toronto, Ontario", "Vancouver, BC", "Montreal, Quebec", "Calgary, Alberta",
    # Australia
    "Sydney, NSW", "Melbourne, VIC", "Brisbane, QLD", "Perth, WA"
]

# 🏥 HIGH INTENT TOPICS
TOPICS = [
    "Salon", "Barber Shop", "Spa", "Nail Salon", "Gym", "Yoga Studio",
    "Dentist", "Chiropractor", "Veterinarian", "Dermatologist", "Physiotherapy",
    "Plumber", "Electrician", "HVAC", "Roofing Contractor", "Landscaper",
    "Restaurant", "Cafe", "Bakery", "Pizza Place", "Burger Joint",
    "Auto Repair", "Car Detailer", "Tire Shop", "Real Estate Agency", "Florist",
    "Law Firm", "Accountant", "Insurance Agency", "Cleaning Service"
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    try: requests.post(url, json=payload)
    except: pass

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

# --- 🧠 SMART ROTATION LOGIC (Unique Topic per City) ---
def get_smart_target():
    # 1. Load purani history (kya check ho chuka hai)
    if os.path.exists('combinations.json'):
        with open('combinations.json', 'r') as f: done_combos = json.load(f)
    else:
        done_combos = []

    # 2. Saare possible combinations banao (City x Topic)
    all_possible = [f"{city}|{topic}" for city in LOCATIONS for topic in TOPICS]
    
    # 3. Jo ho chuke hain unhe hata do
    remaining = list(set(all_possible) - set(done_combos))
    
    # 4. Agar sab khatam ho gaya to Reset karo
    if not remaining:
        done_combos = []
        remaining = all_possible

    # 5. Random naya select karo
    selection = random.choice(remaining)
    city, topic = selection.split('|')
    
    # 6. Save karo taki agli bar repeat na ho
    done_combos.append(selection)
    with open('combinations.json', 'w') as f: json.dump(done_combos, f)
    
    return city, topic

def run_scraper():
    driver = get_driver()
    
    if os.path.exists('history.json'):
        with open('history.json', 'r') as f: history = json.load(f)
    else: history = []

    total_leads_found = 0
    attempts = 0
    scraped_data = []

    # 🔄 MAIN LOOP: Jab tak 3 leads na mile ya 5 cities check na kar le
    while total_leads_found < TARGET_LEADS and attempts < MAX_ATTEMPTS:
        attempts += 1
        city, topic = get_smart_target() # <--- Yahan Smart Rotation call ho raha hai
        query = f"{topic} in {city}"
        
        print(f"\n🔄 Attempt {attempts}: Searching '{query}'")
        
        try:
            driver.get(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
            time.sleep(5)
            
            # Scroll Feed
            try:
                feed = driver.find_element(By.CSS_SELECTOR, "div[role='feed']")
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed)
                time.sleep(3)
            except: pass

            # Top 15 Results Check
            listings = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")[:15]
            
            for listing in listings:
                try:
                    listing.click()
                    time.sleep(random.uniform(2, 4))
                    
                    name = driver.find_element(By.TAG_NAME, "h1").text
                    if name in history: continue 

                    # Extract Details
                    try: website = driver.find_element(By.CSS_SELECTOR, "a[data-item-id='authority']").get_attribute("href")
                    except: website = ""

                    try: phone = driver.find_element(By.CSS_SELECTOR, "button[data-item-id^='phone:']").get_attribute("aria-label").replace("Phone: ", "")
                    except: phone = "Not Listed"

                    try: 
                        rating_text = driver.find_element(By.CSS_SELECTOR, "div.F7nice").text
                        rating = rating_text.split("\n")[0]
                        reviews = rating_text.split("\n")[1]
                    except: rating = "N/A"; reviews = "(0)"

                    # --- GOLD FILTER ---
                    is_gold = False
                    status = "✅ Active"
                    
                    # Condition 1: Website Gayab Hai
                    if not website:
                        is_gold = True; status = "❌ No Website (GOLD)"
                    # Condition 2: Website Bekaar Hai (FB/Wix)
                    elif any(x in website.lower() for x in ['facebook.com', 'wix.com', 'business.site', 'wordpress.com']):
                        is_gold = True; status = f"⚠️ Weak ({website})"

                    # Condition 3: Reviews 15+ hone chahiye
                    review_count = int(''.join(filter(str.isdigit, reviews))) if any(c.isdigit() for c in reviews) else 0

                    if is_gold and review_count >= 15:
                        msg = (
                            f"🟦 *{topic.upper()} | {city.split(',')[0].upper()}*\n\n"
                            f"🏪 *Name:* {name}\n"
                            f"📞 *Phone:* `{phone}`\n"
                            f"🌐 *Status:* {status}\n"
                            f"⭐ *Rating:* {rating} ({reviews})\n"
                            f"🔗 [Maps Link]({driver.current_url})"
                        )
                        send_telegram(msg)
                        
                        scraped_data.append({"Name": name, "Category": topic, "City": city, "Phone": phone, "Website": status})
                        history.append(name)
                        total_leads_found += 1
                        print(f"   ✅ FOUND: {name}")
                        
                        if total_leads_found >= TARGET_LEADS: break
                
                except: continue
        except: continue

    driver.quit()

    # Save History & New Combinations
    with open('history.json', 'w') as f: json.dump(history, f)
    
    if scraped_data:
        df = pd.DataFrame(scraped_data)
        df.to_csv('leads.csv', mode='a', index=False, header=not os.path.exists('leads.csv'))

    # Final Report
    report_msg = f"📊 *REPORT:* Checked {attempts} locations. Found {total_leads_found} GOLD leads."
    send_telegram(report_msg)

if __name__ == "__main__":
    run_scraper()
