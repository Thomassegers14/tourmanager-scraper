from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import pandas as pd

# Altijd relatief aan de scraper/ root, ongeacht de werkdirectory
BASE_DIR = Path(__file__).parent.parent

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_csv(path: Path):
    if path.exists():
        return pd.read_csv(path).to_dict(orient="records")
    return {"error": f"Bestand niet gevonden: {path.name}"}


# ----- Endpoints -----
@app.get("/", tags=["Info"])
def root():
    return {"status": "API running", "message": "Welcome to TourManager Scraper API"}

@app.get("/startlist/{event_id}/{year}", tags=["Startlist"])
def get_startlist(event_id: str, year: int):
    return _read_csv(BASE_DIR / f"data/processed/startlists/startlist_{event_id}_{year}.csv")

@app.get("/startlist_favorites/{event_id}/{year}", tags=["Startlist"])
def get_startlist_favorites(event_id: str, year: int):
    return _read_csv(BASE_DIR / f"data/processed/startlists_favorites/startlist_{event_id}_{year}.csv")

@app.get("/stages/{event_id}/{year}", tags=["Stages"])
def get_stages(event_id: str, year: int):
    return _read_csv(BASE_DIR / f"data/processed/stages/stages_{event_id}_{year}.csv")

@app.get("/results/{event_id}/{year}", tags=["Results"])
def get_results(event_id: str, year: int):
    return _read_csv(BASE_DIR / f"data/processed/results/{event_id}_{year}_all_stage_results.csv")

@app.get("/selections/{event_id}/{year}", tags=["Selections"])
def get_selections(event_id: str, year: int):
    return _read_csv(BASE_DIR / f"data/processed/selections/selections_{event_id}_{year}.csv")

@app.get("/ranking/{event_id}/{year}", tags=["Ranking"])
def get_ranking_by_stage(event_id: str, year: int):
    return _read_csv(BASE_DIR / f"data/processed/ranking/ranking_by_stage_{event_id}_{year}.csv")

@app.get("/points/{event_id}/{year}", tags=["Points"])
def get_points_by_stage(event_id: str, year: int):
    return _read_csv(BASE_DIR / f"data/processed/points/rider_stage_summary_{event_id}_{year}.csv")
