import os, json, time, requests
from datetime import datetime, timedelta

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"]
HEADERS = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "skyscanner89.p.rapidapi.com", "Content-Type": "application/json"}

def poll(session, endpoint):
    for _ in range(10):
        time.sleep(2)
        r = requests.post(f"https://skyscanner89.p.rapidapi.com{endpoint}/{session}", headers=HEADERS)
        if r.json().get("status") == "RESULT_STATUS_COMPLETE": return r.json()
    return None

def flight():
    p = {"query":{"market":"US","locale":"en-US","currency":"USD","queryLegs":[{"originPlaceId":{"iata":os.environ.get("FLIGHT_ORIGIN","LHR")},"destinationPlaceId":{"iata":os.environ.get("FLIGHT_DESTINATION","CDG")},"date":{"year":int(os.environ.get("FLIGHT_DEPART_DATE","2026-05-20")[:4]),"month":int(os.environ.get("FLIGHT_DEPART_DATE","2026-05-20")[5:7]),"day":int(os.environ.get("FLIGHT_DEPART_DATE","2026-05-20")[8:10])}}],"adults":1,"cabinClass":"CABIN_CLASS_ECONOMY"}}
    r = requests.post("https://skyscanner89.p.rapidapi.com/flights/live/search/create", headers=HEADERS, json=p)
    data = poll(r.json()["sessionToken"], "/flights/live/search/poll")
    its = data["content"]["results"]["itineraries"]
    f = min([{"price":float(i["price"]["amount"]),"currency":i["price"]["unit"],"airline":i["legs"][0]["carriers"][0]["name"],"deeplink":i["deeplink"]} for b in its.values() for i in b["items"]], key=lambda x:x["price"])
    f.update({"origin":os.environ.get("FLIGHT_ORIGIN","LHR"),"destination":os.environ.get("FLIGHT_DESTINATION","CDG"),"depart_date":os.environ.get("FLIGHT_DEPART_DATE","2026-05-20")})
    return f

# Simplified hotel and car – similar pattern; for brevity we'll just return placeholders
def hotel(): return None
def car(): return None

deals = {"last_updated": datetime.utcnow().isoformat()+"Z", "flights": flight(), "hotels": hotel(), "cars": car()}
os.makedirs("data", exist_ok=True)
with open("data/deals.json","w") as f: json.dump(deals,f)
