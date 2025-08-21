from fastapi import FastAPI
import pandas as pd
import os

app = FastAPI(title="TourManager Scraper API")

@app.get("/")
def root():
    return {"status": "API running", "message": "Welcome to TourManager Scraper API"}

@app.get("/startlist/{event_id}/{year}")
def get_startlist(event_id: str, year: int):
    file_path = f"data/processed/startlists/startlist_{event_id}_{year}.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        return df.to_dict(orient="records")
    return {"error": "No startlist found"}

@app.get("/stages/{event_id}/{year}")
def get_stages(event_id: str, year: int):
    file_path = f"data/processed/stages/stages_{event_id}_{year}.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        return df.to_dict(orient="records")
    return {"error": "No stages found"}

@app.get("/results/{event_id}/{year}")
def get_results(event_id: str, year: int):
    file_path = f"data/processed/results/{event_id}_{year}_all_stage_results.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        return df.to_dict(orient="records")
    return {"error": "No results found"}
