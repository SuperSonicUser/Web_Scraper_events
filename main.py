from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scraper import run_scraper  # assuming it's in scraper.py

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/events")
def fetch_live_events():
    events = run_scraper()
    return events
