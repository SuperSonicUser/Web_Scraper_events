from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scraper import run_scraper
import os
import json

app = FastAPI()

# Enable CORS for all origins (for Expo mobile app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional root route (good for testing)
@app.get("/")
def root():
    return {"message": "FastAPI is running! Visit /events to fetch scraped event data."}

#  MAIN endpoint — triggers scraping, saves JSON, returns events
@app.get("/events")
def update_and_get_events():
    try:
        events = run_scraper()  # Run the actual scraper
        return {"status": "success", "events": events}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)

    # Run the scraper and save results to JSON
    try:
        events = run_scraper()
        with open("data/events.json", "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=4)
        print("✅ Events saved to data/events.json")
    except Exception as e:
        print(f"❌ Error running scraper: {e}")