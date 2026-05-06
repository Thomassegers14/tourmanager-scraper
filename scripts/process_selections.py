# scripts/process_selections.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from config import EVENT_YEARS, BASE_DIR


def get_selections() -> pd.DataFrame:
    """Haal alle inzendingen op uit PostgreSQL."""
    load_dotenv(BASE_DIR / ".Renviron")

    con = psycopg2.connect(
        dbname   = os.environ["DB_NAME"],
        host     = os.environ["DB_HOST"],
        port     = int(os.environ["DB_PORT"]),
        user     = os.environ["DB_USER"],
        password = os.environ["DB_PASS"],
        sslmode  = "require",
    )
    try:
        df = pd.read_sql("SELECT * FROM inzendingen", con)
    finally:
        con.close()

    return df


def process_selections(df: pd.DataFrame) -> pd.DataFrame:
    """Verwerk ruwe inzendingen naar één rij per renner per deelnemer."""
    # PostgreSQL array-literals opschonen: {, }, " verwijderen
    for col in ["rider_ids", "rider_names"]:
        df[col] = df[col].str.replace(r'[{}"]', "", regex=True)

    # Komma-gescheiden string → lijst → explode
    df["rider_ids"]   = df["rider_ids"].str.split(",")
    df["rider_names"] = df["rider_names"].str.split(",")
    df = df.explode("rider_ids").explode("rider_names")
    df = df.rename(columns={"rider_ids": "rider_id", "rider_names": "rider_name"})

    # Witruimte verwijderen
    str_cols = df.select_dtypes("object").columns
    df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())

    # Meest recente inzending per deelnemer bewaren
    df = (
        df
        .sort_values("tijdstip")
        .groupby(["voornaam", "achternaam", "email"], group_keys=False)
        .apply(lambda g: g[g["tijdstip"] == g["tijdstip"].max()])
    )

    return df[["id", "tijdstip", "voornaam", "achternaam", "email", "rider_id", "rider_name"]]


def main() -> None:
    print("\n=== Processing selections ===")

    try:
        raw = get_selections()
    except Exception as e:
        print(f"  [ERROR] Database verbinding mislukt: {e}")
        return

    selections = process_selections(raw)
    selections = selections[~selections["achternaam"].str.lower().str.contains("test", na=False)]

    out_dir = BASE_DIR / "data" / "processed" / "selections"
    out_dir.mkdir(parents=True, exist_ok=True)

    for ev in EVENT_YEARS:
        out_file = out_dir / f"selections_{ev['event_id']}_{ev['event_year']}.csv"
        selections.to_csv(out_file, index=False)
        print(f"  Opgeslagen: {out_file} ({len(selections)} rijen)")

    print("=== Klaar: selections ===")


if __name__ == "__main__":
    main()
