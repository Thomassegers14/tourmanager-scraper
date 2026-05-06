# scripts/run_scrape_stages.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from io import StringIO
from datetime import date

import pandas as pd

from config import EVENT_YEARS, BASE_URL, BASE_DIR
from utils import read_page

STAGE_TYPES: dict[str, str] = {
    "p1": "Flat",
    "p2": "Hills, flat finish",
    "p3": "Hills, uphill finish",
    "p4": "Mountains, flat finish",
    "p5": "Mountains, uphill finish",
}


def scrape_stages(event_id: str, year: int) -> pd.DataFrame:
    print(f"  Fetching stages page...")
    soup = read_page(f"{BASE_URL}/race/{event_id}/{year}/route/stages")

    tables = soup.find_all("table")
    if len(tables) < 2:
        raise ValueError(f"Verwacht minstens 2 tabellen, gevonden: {len(tables)}")

    # ── Eerste tabel: etappes ─────────────────────────────────────────────────
    df = pd.read_html(StringIO(str(tables[0])))[0]
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, df.columns != ""]  # lege kolommen weg

    # Stage IDs uit href van 3e kolom
    stage_ids = [a.get("href") for a in tables[0].select("tbody tr td:nth-child(3) a")]

    # Stage type codes uit .profile class
    stage_type_codes = []
    for el in tables[0].select(".profile"):
        for cls in el.get("class", []):
            if cls.startswith("p") and len(cls) == 2 and cls[1].isdigit():
                stage_type_codes.append(cls)
                break

    # Lege datumrijen filteren
    date_col = next((c for c in df.columns if c.lower() == "date"), df.columns[0])
    df = df[df[date_col].notna() & (df[date_col].astype(str).str.strip() != "")]

    hash_col     = next((c for c in df.columns if c == "#"), df.columns[0])
    departure_col = next((c for c in df.columns if "departure" in c.lower()), None)
    arrival_col   = next((c for c in df.columns if "arrival"   in c.lower()), None)
    distance_col  = next((c for c in df.columns if "distance"  in c.lower()), None)
    vert_col      = next((c for c in df.columns if "vertical"  in c.lower()), None)

    stage_nr = df[hash_col].astype(str).str.extract(r"(\d+)")[0]
    dates    = pd.to_datetime(
        df[date_col].astype(str) + f"/{year}", format="%d/%m/%Y", errors="coerce"
    )

    n = min(len(df), len(stage_ids))
    stages = pd.DataFrame({
        "stage_id":   stage_ids[:n],
        "date":       dates.iloc[:n].values,
        "stage":      pd.to_numeric(stage_nr.iloc[:n], errors="coerce"),
        "stage_name": df[hash_col].iloc[:n].values,
        "stage_type": [STAGE_TYPES.get(c, c) for c in (stage_type_codes[:n] + [None] * n)][:n],
        "departure":  df[departure_col].iloc[:n].values if departure_col else None,
        "arrival":    df[arrival_col].iloc[:n].values   if arrival_col   else None,
        "distance_km": pd.to_numeric(
            df[distance_col].astype(str).str.replace(",", "."), errors="coerce"
        ).iloc[:n].values if distance_col else None,
        "vertical_m": pd.to_numeric(
            df[vert_col].astype(str).str.replace(",", "."), errors="coerce"
        ).iloc[:n].values if vert_col else None,
    })

    # ── Tweede tabel: moeilijkste etappes (profile score) ────────────────────
    df2 = pd.read_html(StringIO(str(tables[1])))[0]
    df2.columns = ["stage_rank", "stage_name_h", "profile_score"]
    hardest_ids = [a.get("href") for a in tables[1].select("tbody tr td:nth-child(2) a")]

    hardest = pd.DataFrame({
        "stage_id":     hardest_ids[:len(df2)],
        "profile_score": pd.to_numeric(
            df2["profile_score"].astype(str).str.extract(r"(\d+)")[0], errors="coerce"
        ),
    })

    result = stages.merge(hardest, on="stage_id", how="left")
    result = result.sort_values("stage").reset_index(drop=True)
    print(f"  Stages: {len(result)} etappes")
    return result


def main() -> None:
    for ev in EVENT_YEARS:
        event_id   = ev["event_id"]
        event_year = ev["event_year"]

        print(f"\n=== Scraping stages: {event_id} {event_year} ===")
        stages = scrape_stages(event_id, event_year)

        out_dir = BASE_DIR / "data" / "processed" / "stages"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"stages_{event_id}_{event_year}.csv"
        stages.to_csv(out_file, index=False)
        print(f"  Opgeslagen: {out_file}")
        print(f"=== Klaar: {event_id} {event_year} ===")


if __name__ == "__main__":
    main()
