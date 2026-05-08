# scripts/process_selections.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

from config import EVENT_YEARS, BASE_DIR


def get_selections() -> pd.DataFrame:
    """Haal alle inzendingen op via de Supabase REST API."""
    load_dotenv(BASE_DIR / ".Renviron")

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]

    client = create_client(url, key)
    response = client.table("inzendingen").select("*").execute()
    return pd.DataFrame(response.data)


def process_selections(df: pd.DataFrame) -> pd.DataFrame:
    """Verwerk ruwe inzendingen naar één rij per renner per deelnemer per event."""
    # Supabase geeft rider_ids en rider_names al als Python-lijsten terug
    df = df.explode(["rider_ids", "rider_names"])
    df = df.rename(columns={"rider_ids": "rider_id", "rider_names": "rider_name"})

    # Witruimte verwijderen
    str_cols = df.select_dtypes("object").columns
    df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())

    # Meest recente inzending per deelnemer per event bewaren
    df = (
        df
        .sort_values("tijdstip")
        .groupby(["voornaam", "achternaam", "email", "event_id", "event_year"], group_keys=False)
        .apply(lambda g: g[g["tijdstip"] == g["tijdstip"].max()])
    )

    return df[[
        "id", "tijdstip", "voornaam", "achternaam", "email",
        "event_id", "event_year", "rider_id", "rider_name",
    ]]


def main() -> None:
    print("\n=== Processing selections ===")

    try:
        raw = get_selections()
    except Exception as e:
        print(f"  [ERROR] Supabase verbinding mislukt: {e}")
        return

    selections = process_selections(raw)
    selections = selections[~selections["achternaam"].str.lower().str.contains("test", na=False)]

    out_dir = BASE_DIR / "data" / "processed" / "selections"
    out_dir.mkdir(parents=True, exist_ok=True)

    for ev in EVENT_YEARS:
        ev_sel = selections[
            (selections["event_id"]   == ev["event_id"]) &
            (selections["event_year"] == ev["event_year"])
        ]
        out_file = out_dir / f"selections_{ev['event_id']}_{ev['event_year']}.csv"
        ev_sel.to_csv(out_file, index=False)
        print(f"  Opgeslagen: {out_file} ({len(ev_sel)} rijen)")

    print("=== Klaar: selections ===")


if __name__ == "__main__":
    main()
