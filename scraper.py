import os, re, json, requests, subprocess, time
from dotenv import load_dotenv
from cloudinary.uploader import upload as cloudinary_upload
from cloudinary.utils import cloudinary_url
import cloudinary
from playwright.sync_api import sync_playwright, TimeoutError

# Load .env variables
load_dotenv()

# Configure Cloudinary
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
    max_retries = 10
    url = "https://csuohio.presence.io/events"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Retry logic like original Selenium code
            for attempt in range(1, max_retries + 1):
                print(f"🔁 Attempt {attempt}: Loading event page...")
                page.goto(url, timeout=60000)
                time.sleep(2)

                try:
                    page.wait_for_selector("div.card.ng-scope.focused-card", timeout=10000)
                    print("✅ Event cards loaded successfully.\n")
                    break
                except TimeoutError:
                    print("⚠️ Event cards not loaded. Refreshing page...\n")
                    page.reload()
                    time.sleep(2)
            else:
                print("❌ Failed to load events after multiple retries.")
                browser.close()
                return []

            # Define scraper for each page
            def scrape_events_on_page():
                page.wait_for_selector("div.card.ng-scope.focused-card", timeout=10000)
                return page.query_selector_all("div.card.ng-scope.focused-card")

            while True:
                try:
                    events = scrape_events_on_page()
                    print(f"✅ Found {len(events)} events on this page.")

                    for event in events:
                        try:
                            title_el = event.query_selector("h2 a")
                            org_el = event.query_selector("small.org-name a")
                            date_el = event.query_selector("small[aria-label*='start date and time']")
                            loc_el = event.query_selector("small[aria-label*='location']")

                            name = title_el.inner_text() if title_el else "Untitled"
                            org = org_el.inner_text() if org_el else "Unknown Org"
                            dt = date_el.inner_text() if date_el else "Date TBD"
                            loc = loc_el.inner_text() if loc_el else "Location TBD"

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
                                "id": len(results) + 1,
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

                            print(f"✅ Scraped: {name}")

                        except Exception as e:
                            print(f"❌ Skipping one event: {e}")

                    # Handle pagination
                    next_button = page.query_selector("a[aria-label='Next page of results'].has-items")
                    if next_button and "disabled" not in next_button.get_attribute("class"):
                        print("➡️ Navigating to next page...\n")
                        next_button.click()
                        page.wait_for_timeout(3000)
                    else:
                        print("✅ No more pages to scrape.")
                        break

                except Exception as e:
                    print("❌ Error during pagination:", e)
                    break

            browser.close()

    except Exception as e:
        print("Playwright runtime error:", e)

    # Save results to JSON
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/events.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n🎉 Saved {len(results)} events to data/events.json")
    except Exception as e:
        print("Error saving JSON file:", e)

    return results
