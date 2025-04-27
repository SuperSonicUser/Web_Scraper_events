import os, re, json, requests, subprocess
from dotenv import load_dotenv
from cloudinary.uploader import upload as cloudinary_upload
from cloudinary.utils import cloudinary_url
import cloudinary
from playwright.sync_api import sync_playwright

# Load environment variables
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
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled"
                ]
            )

            page = browser.new_page(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/113.0.0.0 Safari/537.36"
            ))
            page.set_viewport_size({"width": 1280, "height": 800})

            events = []

            for attempt in range(1, max_retries + 1):
                print(f"🔁 Attempt {attempt}: Loading event page...")
                try:
                    page.goto(url, timeout=120000)

                    # Smart wait for the event cards
                    try:
                        page.wait_for_selector("div.card.ng-scope.focused-card", timeout=30000)
                    except Exception as e:
                        print(f"⚠️ Smart wait error: {e}")
                        page.wait_for_timeout(5000)  # fallback fixed wait

                    events = page.query_selector_all("div.card.ng-scope.focused-card")

                    if len(events) > 0:
                        print(f"✅ Found {len(events)} event cards on first page.\n")
                        break
                    else:
                        print("⚠️ No event cards found. Retrying...\n")
                        page.reload(wait_until="domcontentloaded")
                        page.wait_for_timeout(3000)

                except Exception as e:
                    print(f"Page load error: {e}")

            else:
                print("❌ Failed to load events after multiple retries.")
                browser.close()
                return []

            def scrape_events_on_page():
                local_results = []
                current_events = page.query_selector_all("div.card.ng-scope.focused-card")
                print(f"📄 Scraping {len(current_events)} events on this page...")

                for event in current_events:
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
                                try:
                                    img_data = requests.get(raw_img).content
                                    image_url = upload_to_cloudinary(img_data, name)
                                except Exception as e:
                                    print(f"❌ Image fetch error: {e}")

                        local_results.append({
                            "id": len(results) + len(local_results) + 1,
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

                return local_results

            # Scrape first page
            results.extend(scrape_events_on_page())

            # Pagination
            while True:
                next_button = page.query_selector("a[aria-label='Next page of results'].has-items")
                if next_button and "disabled" not in (next_button.get_attribute("class") or ""):
                    print("➡️ Navigating to next page...")
                    next_button.click()
                    page.wait_for_timeout(3000)
                    results.extend(scrape_events_on_page())
                else:
                    print("✅ No more pages to scrape.")
                    break

            browser.close()

    except Exception as e:
        print("Playwright runtime error:", e)

    # Save scraped data to JSON
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/events.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n🎉 Saved {len(results)} events to data/events.json")
    except Exception as e:
        print("Error saving JSON file:", e)

    return results
