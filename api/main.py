from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
import pandas as pd
import os

# ----- Veilige CSV-lezer -----
def read_csv_safe(file_path):
    """
    Lees CSV en zet alle NaN / NA waarden om naar None voor JSON compatibiliteit.
    """
    if not os.path.exists(file_path):
        return None
    df = pd.read_csv(file_path, encoding="utf-8")
    df = df.replace("NA", None).where(pd.notnull(df), None)
    return jsonable_encoder(df)

# ----- FastAPI instantie -----
app = FastAPI(
    title="TourManager Scraper API",
    description="""
    API om gescrapete data van TourManager beschikbaar te maken.

    **Beschikbare endpoints:**
    - `/startlist/{event_id}/{year}` → startlijst
    - `/startlists_favorites/{event_id}/{year}` → verrijkte startlijst
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
origins = ["*"]  # Voor development; later specifieker instellen
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Endpoints -----
@app.get("/", tags=["Info"])
def root():
    return {"status": "API running", "message": "Welcome to TourManager Scraper API"}

@app.get("/startlist/{event_id}/{year}", tags=["Startlist"])
def get_startlist(event_id: str, year: int):
    file_path = f"data/processed/startlists/startlist_{event_id}_{year}.csv"
    data = read_csv_safe(file_path)
    if data is not None:
        return data
    return {"error": "No startlist found"}

@app.get("/startlists_favorites/{event_id}/{year}", tags=["Startlist"])
def get_startlist_favorites(event_id: str, year: int):
    file_path = f"data/processed/startlists_favorites/startlist_{event_id}_{year}.csv"
    data = read_csv_safe(file_path)
    if data is not None:
        return data
    return {"error": "No startlist_favorites found"}

@app.get("/stages/{event_id}/{year}", tags=["Stages"])
def get_stages(event_id: str, year: int):
    file_path = f"data/processed/stages/stages_{event_id}_{year}.csv"
    data = read_csv_safe(file_path)
    if data is not None:
        return data
    return {"error": "No stages found"}

@app.get("/results/{event_id}/{year}", tags=["Results"])
def get_results(event_id: str, year: int):
    file_path = f"data/processed/results/{event_id}_{year}_all_stage_results.csv"
    data = read_csv_safe(file_path)
    if data is not None:
        return data
    return {"error": "No results found"}
