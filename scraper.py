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
    # 👇 Install Chromium at runtime if not present (Render free plan workaround)
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        print("Playwright Chromium already installed or failed to install:", e)

    results = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://csuohio.presence.io/events", timeout=60000)

            page.wait_for_selector("div.card.focused-card")
            events = page.query_selector_all("div.card.focused-card")

            for i, event in enumerate(events):
                try:
                    name = event.query_selector("h2 a").inner_text()
                    org = event.query_selector("small.org-name a").inner_text()
                    dt = event.query_selector("small[aria-label*='start date and time']").inner_text()
                    loc = event.query_selector("small[aria-label*='location']").inner_text()

                    # Extract image from background-image style
                    image_url = ""
                    image_style = event.query_selector("div.featured-org-img")
                    if image_style:
                        style = image_style.get_attribute("style")
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
                    print("Skipping event due to:", e)

            browser.close()

    except Exception as e:
        print("Error launching Playwright browser:", e)

    # Save scraped results to JSON
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/events.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error saving JSON file:", e)

    return results
