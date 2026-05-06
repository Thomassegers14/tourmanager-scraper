# scripts/compute_rider_points.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd

from config import EVENT_YEARS, BASE_DIR, STAGE_POINTS, STAGE_POINTS_TTT, DAILY_CLASS_POINTS, FINAL_CLASS_POINTS


def main() -> None:
    for ev in EVENT_YEARS:
        event_id   = ev["event_id"]
        event_year = ev["event_year"]

        print(f"\n=== Computing rider points: {event_id} {event_year} ===")

        # ── Data inladen ──────────────────────────────────────────────────────
        results_file = BASE_DIR / "data" / "processed" / "results" / f"{event_id}_{event_year}_all_stage_results.csv"
        if not results_file.exists():
            print(f"  [SKIP] Geen resultaten beschikbaar voor {event_id} {event_year}")
            continue

        startlist = pd.read_csv(BASE_DIR / "data" / "processed" / "startlists_favorites" / f"startlist_{event_id}_{event_year}.csv")
        stages    = pd.read_csv(BASE_DIR / "data" / "processed" / "stages"               / f"stages_{event_id}_{event_year}.csv")
        results   = pd.read_csv(results_file)

        stage_info = stages[["stage_id", "stage"]].copy()
        stage_info["stage"] = pd.to_numeric(stage_info["stage"], errors="coerce").astype("Int64")

        last_stage_id = stage_info.loc[stage_info["stage"] == stage_info["stage"].max(), "stage_id"].iloc[0]
        ttt_stages    = set(stages.loc[stages["stage_name"].str.contains(r"\(TTT\)", na=False), "stage_id"])

        # ── Etappe punten ─────────────────────────────────────────────────────
        stage_results = (
            results[results["category"] == "stage"]
            .assign(rank=lambda d: pd.to_numeric(d["rank"], errors="coerce"))
            .dropna(subset=["rank"])
            .query("rank <= 10")
            .copy()
        )
        stage_results["is_ttt"] = stage_results["stage_id"].isin(ttt_stages)
        stage_results["points"] = stage_results.apply(
            lambda r: STAGE_POINTS_TTT.get(int(r["rank"]), 0) if r["is_ttt"]
                      else STAGE_POINTS.get(int(r["rank"]), 0),
            axis=1,
        )
        stage_results = stage_results[["stage_id", "rider_id", "points"]]

        # ── Dagelijkse klassementen ───────────────────────────────────────────
        daily_results = (
            results[
                (results["category"].isin(["gc", "kom", "points", "youth"])) &
                (results["stage_id"] != last_stage_id)
            ]
            .assign(rank=lambda d: pd.to_numeric(d["rank"], errors="coerce"))
            .dropna(subset=["rank"])
            .query("rank <= 3")
            .copy()
        )
        daily_results["points"] = daily_results.apply(
            lambda r: DAILY_CLASS_POINTS.get((r["category"], int(r["rank"])), 0), axis=1
        )
        daily_results = daily_results[["stage_id", "rider_id", "points"]]

        # ── Eindklassementen ──────────────────────────────────────────────────
        final_results = (
            results[
                (results["category"].isin(["gc", "kom", "points", "youth"])) &
                (results["stage_id"] == last_stage_id)
            ]
            .assign(rank=lambda d: pd.to_numeric(d["rank"], errors="coerce"))
            .dropna(subset=["rank"])
            .copy()
        )
        final_results = final_results[
            ((final_results["category"] == "gc") & (final_results["rank"] <= 20)) |
            ((final_results["category"] != "gc") & (final_results["rank"] <= 5))
        ].copy()
        final_results["points"]   = final_results.apply(
            lambda r: FINAL_CLASS_POINTS.get((r["category"], int(r["rank"])), 0), axis=1
        )
        final_results["stage_id"] = "final"
        final_results = final_results[["stage_id", "rider_id", "points"]]

        # ── Samenvoegen & per etappe sommeren ─────────────────────────────────
        all_points = (
            pd.concat([stage_results, daily_results, final_results], ignore_index=True)
            .groupby(["stage_id", "rider_id"], as_index=False)["points"]
            .sum()
            .rename(columns={"points": "stage_points"})
        )

        # Stage lookup uitbreiden met "final"
        final_stage_nr = int(stage_info["stage"].max()) + 1
        if not final_results.empty:
            stage_info = pd.concat([
                stage_info,
                pd.DataFrame({"stage_id": ["final"], "stage": [final_stage_nr]})
            ], ignore_index=True)

        all_points_named = (
            all_points
            .merge(startlist[["rider_id", "rider_name"]].drop_duplicates(), on="rider_id", how="left")
            .merge(stage_info, on="stage_id", how="left")
        )

        available_stage_ids = all_points_named["stage_id"].unique()

        # Cross join alle renners × beschikbare etappes
        all_combinations = (
            pd.DataFrame({"stage_id": available_stage_ids})
            .merge(startlist[["rider_id", "rider_name"]].drop_duplicates(), how="cross")
            .merge(stage_info, on="stage_id", how="left")
        )

        rider_summary = (
            all_combinations
            .merge(all_points_named[["stage_id", "rider_id", "stage_points"]],
                   on=["stage_id", "rider_id"], how="left")
            .fillna({"stage_points": 0})
            .sort_values(["rider_id", "stage"])
        )
        rider_summary["cumulative_points"] = rider_summary.groupby("rider_id")["stage_points"].cumsum()
        rider_summary = rider_summary[["rider_id", "rider_name", "stage_id", "stage", "stage_points", "cumulative_points"]]

        # ── Wegschrijven ──────────────────────────────────────────────────────
        out_dir = BASE_DIR / "data" / "processed" / "points"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"rider_stage_summary_{event_id}_{event_year}.csv"
        rider_summary.to_csv(out_file, index=False)
        print(f"  Opgeslagen: {out_file} ({len(rider_summary)} rijen)")
        print(f"=== Klaar: {event_id} {event_year} ===")


if __name__ == "__main__":
    main()
