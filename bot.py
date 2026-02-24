import pandas as pd
import requests
import os
import time
from playwright.sync_api import sync_playwright


TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CITIES=[
("New York","USA",40.7128,-74.0060),
("Los Angeles","USA",34.0522,-118.2437),
("Toronto","Canada",43.6510,-79.3470),
("London","UK",51.5072,-0.1276),
("Sydney","Australia",-33.8688,151.2093),
("Dubai","UAE",25.2048,55.2708)
]

CATEGORIES=[
"dental clinic",
"chiropractor",
"roofing contractor",
"law firm",
"hvac contractor",
"med spa",
"real estate agency"
]

def send(msg):
    requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")

def load_history():
    if os.path.exists("history.csv"):
        return pd.read_csv("history.csv")
    return pd.DataFrame(columns=["phone"])

def save_history(df):
    df.to_csv("history.csv",index=False)

def get_text(page,xpath):
    try:
        return page.locator(xpath).inner_text(timeout=2000)
    except:
        return ""

def scrape():
    history=load_history()
    phones=set(history["phone"].astype(str))

    leads=[]

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page()

        for city,country,lat,lon in CITIES:
            for cat in CATEGORIES:

                if len(leads)>=5:
                    break

                url=f"https://www.google.com/maps/@{lat},{lon},14z"
                page.goto(url)
                time.sleep(5)

                search=f"{cat} in {city}"
                page.fill('//input[@id="searchboxinput"]',search)
                page.keyboard.press("Enter")
                time.sleep(6)

                listings=page.locator('//div[contains(@class,"Nv2PK")]')

                for i in range(min(listings.count(),10)):
                    if len(leads)>=5:
                        break

                    listings.nth(i).click()
                    time.sleep(4)

                    name=get_text(page,'//h1')
                    phone=get_text(page,'//button[contains(@data-item-id,"phone")]')
                    address=get_text(page,'//button[contains(@data-item-id,"address")]')
                    website=get_text(page,'//a[contains(@data-item-id,"authority")]')
                    rating=get_text(page,'//span[@role="img"]')

                    if phone=="" or phone in phones:
                        continue

                    if website!="":
                        continue

                    maplink=page.url

                    leads.append({
                        "name":name,
                        "phone":phone,
                        "category":cat,
                        "address":address,
                        "city":city,
                        "country":country,
                        "map":maplink
                    })

                    phones.add(phone)

        browser.close()

    return leads,phones

def send_leads(leads):
    if not leads:
        send("No new leads today")
        return

    for L in leads:
        msg=f"""
🏢 {L['name']}
📂 {L['category']}
📍 {L['address']}
🌎 {L['city']}, {L['country']}
☎ {L['phone']}
🗺 {L['map']}
"""
        send(msg)
        time.sleep(3)

def main():
    leads,phones=scrape()
    send_leads(leads)
    save_history(pd.DataFrame({"phone":list(phones)}))

if __name__=="__main__":
    main()
