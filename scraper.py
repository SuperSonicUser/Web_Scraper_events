import requests, re, base64
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
from dotenv import load_dotenv

load_dotenv()

IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")


def upload_to_imgbb(image_bytes, event_name):
    encoded = base64.b64encode(image_bytes)
    payload = {
        "key": IMGBB_API_KEY,
        "image": encoded,
        "name": event_name.replace(" ", "_")
    }
    res = requests.post("https://api.imgbb.com/1/upload", data=payload)
    if res.status_code == 200:
        return res.json()["data"]["url"]
    return ""


def run_scraper():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://csuohio.presence.io/events")

    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='card ng-scope focused-card']")))

    results = []

    def scrape_images(event):
        image_elements = event.find_elements(By.CSS_SELECTOR, "div.featured-org-img[ng-if='vm.event.hasCoverImage']")
        image_urls = []
        for element in image_elements:
            style = element.get_attribute("style")
            match = re.search(r"background-image: url\\((.*?)\\)", style)
            if match:
                image_urls.append(match.group(1).replace('"', ''))
        return image_urls

    def scrape_events():
        events = driver.find_elements(By.XPATH, "//div[@class='card ng-scope focused-card']")
        for event in events:
            try:
                name = event.find_element(By.XPATH, ".//h2/a").text
                org = event.find_element(By.XPATH, ".//small[@class='org-name']/a").text
                dt = event.find_element(By.XPATH, ".//small[contains(@aria-label, 'start date and time')]").text
                loc = event.find_element(By.XPATH, ".//small[contains(@aria-label, 'location')]").text
                image_urls = scrape_images(event)
                uploaded_url = ""
                for img_url in image_urls:
                    img_data = requests.get(img_url).content
                    uploaded_url = upload_to_imgbb(img_data, name)
                    break
                results.append({
                    "event_name": name,
                    "organization": org,
                    "date_time": dt,
                    "location": loc,
                    "image_url": uploaded_url
                })
            except Exception as e:
                print("Skipping event due to:", e)

    scrape_events()

    while True:
        try:
            next_button = driver.find_element(By.XPATH, "//a[@aria-label='Next page of results' and contains(@class, 'has-items')]")
            if next_button.is_enabled():
                driver.execute_script("arguments[0].click();", next_button)
                WebDriverWait(driver, 5).until(EC.staleness_of(next_button))
                scrape_events()
            else:
                break
        except:
            break

    driver.quit()
    return results