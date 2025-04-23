from scraper import run_scraper
import json
import os

os.makedirs("data", exist_ok=True)

print("🕒 Running daily scraper...")
events = run_scraper()

with open("data/events.json", "w", encoding="utf-8") as f:
    json.dump(events, f, ensure_ascii=False, indent=2)

print("✅ Events saved to data/events.json")