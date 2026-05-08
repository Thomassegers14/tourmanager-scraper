# scripts/process_stage_results.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd

from config import EVENT_YEARS, BASE_DIR, CATEGORIES
from run_scrape_stages import scrape_stages


def main() -> None:
    for ev in EVENT_YEARS:
        event_id   = ev["event_id"]
        event_year = ev["event_year"]

        print(f"\n=== Processing stage results: {event_id} {event_year} ===")

        raw_dir = BASE_DIR / "data" / "raw" / "results" / event_id / str(event_year)
        csv_files = list(raw_dir.glob("*.csv")) if raw_dir.exists() else []

        if not csv_files:
            print(f"  [SKIP] Geen CSV bestanden gevonden in {raw_dir}")
            continue

        # Alle CSV bestanden inlezen en samenvoegen
        frames = [pd.read_csv(f) for f in csv_files]
        all_results = pd.concat(frames, ignore_index=True)

        # Stages inladen voor stage nummer lookup
        stages_file = BASE_DIR / "data" / "processed" / "stages" / f"stages_{event_id}_{event_year}.csv"
        if stages_file.exists():
            stages = pd.read_csv(stages_file)[["stage_id", "stage"]]
            all_results = all_results.merge(stages, on="stage_id", how="left")
        else:
            print(f"  [WARN] Stages bestand niet gevonden: {stages_file}")
            all_results["stage"] = None

        # Sorteren: stage → categorie (vaste volgorde) → rank → rider_id
        cat_order = {c: i for i, c in enumerate(CATEGORIES)}
        all_results["_cat_ord"]  = all_results["category"].map(cat_order)
        all_results["_rank_num"] = pd.to_numeric(all_results["rank"], errors="coerce")
        all_results = (
            all_results
            .sort_values(["stage", "_cat_ord", "_rank_num", "rider_id"])
            .drop(columns=["_cat_ord", "_rank_num", "stage"])
            .reset_index(drop=True)
        )

        if all_results.empty:
            print(f"  [SKIP] Geen resultaten beschikbaar voor {event_id} {event_year}")
            continue

        out_dir = BASE_DIR / "data" / "processed" / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{event_id}_{event_year}_all_stage_results.csv"
        all_results.to_csv(out_file, index=False)
        print(f"  Opgeslagen: {out_file} ({len(all_results)} rijen)")
        print(f"=== Klaar: {event_id} {event_year} ===")


if __name__ == "__main__":
    main()
