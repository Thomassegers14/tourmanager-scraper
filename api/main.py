from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os

app = FastAPI(
    title="TourManager Scraper API",
    description="""
    API om gescrapete data van TourManager beschikbaar te maken.
    
    **Beschikbare endpoints:**
    - `/startlist/{event_id}/{year}` → startlijst
    - `/stages/{event_id}/{year}` → etappes
    - `/results/{event_id}/{year}` → resultaten
    """,
    version="1.0.0",
    contact={
        "name": "Thomas Segers",
        "url": "https://github.com/Thomassegers14/tourmanager-scraper",
    },
)

# ----- CORS instellen -----
origins = [
    "*"  # Voor development; later specifieker instellen op je domein(s)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Welke domeinen mogen requests doen
    allow_credentials=True,
    allow_methods=["*"],            # GET, POST, etc.
    allow_headers=["*"],            # Alle headers
)

# ----- Endpoints -----
@app.get("/", tags=["Info"])
def root():
    return {"status": "API running", "message": "Welcome to TourManager Scraper API"}

@app.get("/startlist/{event_id}/{year}", tags=["Startlist"])
def get_startlist(event_id: str, year: int):
    file_path = f"data/processed/startlists/startlist_{event_id}_{year}.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        return df.to_dict(orient="records")
    return {"error": "No startlist found"}

@app.get("/stages/{event_id}/{year}", tags=["Stages"])
def get_stages(event_id: str, year: int):
    file_path = f"data/processed/stages/stages_{event_id}_{year}.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        return df.to_dict(orient="records")
    return {"error": "No stages found"}

@app.get("/results/{event_id}/{year}", tags=["Results"])
def get_results(event_id: str, year: int):
    file_path = f"data/processed/results/{event_id}_{year}_all_stage_results.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        return df.to_dict(orient="records")
    return {"error": "No results found"}
