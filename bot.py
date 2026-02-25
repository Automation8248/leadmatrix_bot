import time, csv, os, requests
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

CATEGORIES = [
    "dentist",
    "restaurant",
    "clinic",
    "plumber",
    "real estate",
    "lawyer"
]

CITIES = [
    "New York, USA",
    "London, UK",
    "Toronto, Canada",
    "Sydney, Australia"
]

CSV_FILE = "sent_leads.csv"


# ---------------- TELEGRAM ---------------- #

def send(msg):
    url=f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url,data={"chat_id":CHAT_ID,"text":msg})


# ---------------- HISTORY ---------------- #

def load_history():
    if not os.path.exists(CSV_FILE):
        return set()
    with open(CSV_FILE,"r",encoding="utf8") as f:
        return set(row[0] for row in csv.reader(f))


def save_history(place_id):
    with open(CSV_FILE,"a",newline="",encoding="utf8") as f:
        csv.writer(f).writerow([place_id])


# ---------------- MAP OPEN FIX ---------------- #

def open_maps(page,url):
    page.goto(url)
    for _ in range(6):
        try:
            page.wait_for_selector('//input[@id="searchboxinput"]',timeout=5000)
            return True
        except:
            page.reload()
            time.sleep(5)
    return False


# ---------------- SCRAPER ---------------- #

def scrape():
    history=load_history()
    leads=[]

    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        page=browser.new_page()

        for city in CITIES:
            for cat in CATEGORIES:

                if len(leads)>=2:
                    break

                search=f"{cat} in {city}"
                url=f"https://www.google.com/maps/search/{search.replace(' ','+')}"

                print("Searching:",search)

                if not open_maps(page,url):
                    print("Map failed load")
                    continue

                time.sleep(5)

                listings=page.locator('//a[contains(@href,"/maps/place")]')

                count=min(listings.count(),15)

                for i in range(count):

                    if len(leads)>=2:
                        break

                    listings.nth(i).click()
                    time.sleep(4)

                    link=page.url

                    if link in history:
                        continue

                    try:
                        name=page.locator('//h1').inner_text()
                    except:
                        continue

                    # WEBSITE CHECK (skip if exists)
                    website=""
                    try:
                        website=page.locator('//a[contains(@data-item-id,"authority")]').inner_text()
                    except:
                        website=""

                    if website!="":
                        continue

                    # PHONE
                    phone=""
                    try:
                        phone=page.locator('//button[contains(@data-item-id,"phone")]').inner_text()
                    except:
                        pass

                    # ADDRESS
                    address=""
                    try:
                        address=page.locator('//button[contains(@data-item-id,"address")]').inner_text()
                    except:
                        pass

                    lead=f"""
NEW BUSINESS LEAD

Name: {name}
Category: {cat}
City: {city}

Phone: {phone}
Address: {address}

Map: {link}
                    """

                    leads.append(lead)
                    save_history(link)
                    history.add(link)

        browser.close()

    return leads


# ---------------- MAIN ---------------- #

def main():
    leads=scrape()

    if not leads:
        send("No new leads today")
        return

    send(f"{len(leads)} New Leads Found")

    for l in leads:
        send(l)


if __name__=="__main__":
    main()
