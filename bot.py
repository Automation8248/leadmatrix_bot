import requests, os, csv

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEARCH_QUERY = "dentist in New York"
MAX_LEADS = 2

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def load_history():
    if not os.path.exists("history.csv"):
        return set()
    with open("history.csv","r",encoding="utf-8") as f:
        return set(row[0] for row in csv.reader(f))

def save_history(place_id):
    with open("history.csv","a",newline="",encoding="utf-8") as f:
        csv.writer(f).writerow([place_id])

def search_places():
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.types"
    }
    data = {"textQuery": SEARCH_QUERY}
    r = requests.post(url, headers=headers, json=data)
    return r.json().get("places", [])

def format_msg(p):
    name = p.get("displayName",{}).get("text","N/A")
    phone = p.get("nationalPhoneNumber","N/A")
    address = p.get("formattedAddress","N/A")
    website = p.get("websiteUri","Not Available")
    category = ", ".join(p.get("types",[]))
    map_link = f"https://www.google.com/maps/place/?q=place_id:{p['id']}"
    return f"""Business: {name}
Category: {category}
Phone: {phone}
Address: {address}
Website: {website}
Map: {map_link}"""

def main():
    history = load_history()
    places = search_places()
    sent = 0

    for p in places:
        if sent >= MAX_LEADS:
            break
        if p["id"] in history:
            continue
        if p.get("websiteUri"):
            continue

        send_telegram(format_msg(p))
        save_history(p["id"])
        sent += 1

if __name__ == "__main__":
    main()
