from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/events")
def get_saved_events():
    try:
        with open("data/events.json", "r", encoding="utf-8") as f:
            events = json.load(f)
        return {"status": "success", "events": events}
    except Exception as e:
        return {"status": "error", "message": str(e)}