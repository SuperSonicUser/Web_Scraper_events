from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scraper import run_scraper

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/scrape-events")
def scrape():
    return {"status": "success", "events": run_scraper()}