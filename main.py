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

