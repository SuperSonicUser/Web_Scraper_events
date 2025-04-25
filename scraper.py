import os, re, json, requests, subprocess
from dotenv import load_dotenv
from cloudinary.uploader import upload as cloudinary_upload
from cloudinary.utils import cloudinary_url
import cloudinary
from playwright.sync_api import sync_playwright, TimeoutError

# Load .env variables
load_dotenv()

# Cloudinary setup
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_to_cloudinary(image_bytes, public_id):
    try:
        res = cloudinary_upload(image_bytes, public_id=public_id.replace(" ", "_"))
        return res.get("secure_url", "")
    except Exception as e:
        print("Cloudinary upload failed:", e)
        return ""

def run_scraper():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print("Playwright install error:", e)

    results = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print("Navigating to event page...")
            page.goto("https://csuohio.presence.io/events", timeout=60000)

            try:
                # Wait for visible event cards to load
                page.wait_for_selector("div.card.ng-scope.focused-card", timeout=15000)
            except TimeoutError:
                print("⚠️ Event cards not found on page.")
                browser.close()
                return []

            events = page.query_selector_all("div.card.ng-scope.focused-card")
            print(f"✅ Found {len(events)} events.")

            for i, event in enumerate(events):
                try:
                    name = event.query_selector("h2 a").inner_text()
                    org = event.query_selector("div.org-name").inner_text()
                    dt = event.query_selector("div.date-time").inner_text()
                    loc = event.query_selector("div.location").inner_text()

                    image_url = ""
                    image_el = event.query_selector("div.featured-org-img")
                    if image_el:
                        style = image_el.get_attribute("style")
                        match = re.search(r'url\("?(.*?)"?\)', style)
                        if match:
                            raw_img = match.group(1)
                            img_data = requests.get(raw_img).content
                            image_url = upload_to_cloudinary(img_data, name)

                    results.append({
                        "id": i + 1,
                        "title": name,
                        "organization": org,
                        "date": dt,
                        "time": "",
                        "location": loc,
                        "description": f"{name} by {org}",
                        "category": "General",
                        "attendees": 0,
                        "tags": [],
                        "image": image_url
                    })
                except Exception as e:
                    print("❌ Skipping one event:", e)

            browser.close()

    except Exception as e:
        print("Playwright runtime error:", e)

    # Save to JSON
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/events.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("File save error:", e)

    return results
