# scripts/compute_scores.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd

from config import EVENT_YEARS, BASE_DIR, STAGE_POINTS, STAGE_POINTS_TTT, DAILY_CLASS_POINTS, FINAL_CLASS_POINTS


def main() -> None:
    for ev in EVENT_YEARS:
        event_id   = ev["event_id"]
        event_year = ev["event_year"]

        print(f"\n=== Computing scores: {event_id} {event_year} ===")

        # ── Data inladen ──────────────────────────────────────────────────────
        results_file = BASE_DIR / "data" / "processed" / "results" / f"{event_id}_{event_year}_all_stage_results.csv"
        if not results_file.exists():
            print(f"  [SKIP] Geen resultaten beschikbaar voor {event_id} {event_year}")
            continue

        startlist  = pd.read_csv(BASE_DIR / "data" / "processed" / "startlists_favorites" / f"startlist_{event_id}_{event_year}.csv")
        stages     = pd.read_csv(BASE_DIR / "data" / "processed" / "stages"               / f"stages_{event_id}_{event_year}.csv")
        results    = pd.read_csv(results_file)
        selections = pd.read_csv(BASE_DIR / "data" / "processed" / "selections"           / f"selections_{event_id}_{event_year}.csv")

        stage_info = stages[["stage_id", "stage"]].copy()
        stage_info["stage"] = pd.to_numeric(stage_info["stage"], errors="coerce").astype("Int64")

        last_stage_id = stage_info.loc[stage_info["stage"] == stage_info["stage"].max(), "stage_id"].iloc[0]

        # ── Etappe punten (top 10) ────────────────────────────────────────────
        ttt_stages = set(stages.loc[stages["stage_name"].str.contains(r"\(TTT\)", na=False), "stage_id"])

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

        # ── Dagelijkse klassementen (top 3, niet de laatste etappe) ──────────
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

        # ── Eindklassementen (laatste etappe) ─────────────────────────────────
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

        # ── Stage lookup (inclusief "final") ──────────────────────────────────
        final_stage_nr = int(stage_info["stage"].max()) + 1
        if not final_results.empty:
            stage_info = pd.concat([
                stage_info,
                pd.DataFrame({"stage_id": ["final"], "stage": [final_stage_nr]})
            ], ignore_index=True)

        # ── Punten per deelnemer per etappe ───────────────────────────────────
        all_points = pd.concat([stage_results, daily_results], ignore_index=True)
        all_points_with_stage = all_points.merge(stage_info, on="stage_id", how="left")

        participant_stage_points = (
            all_points_with_stage
            .merge(selections, on="rider_id", how="inner")
            .groupby(["stage", "stage_id", "id", "voornaam", "achternaam"], as_index=False)
            ["points"].sum()
            .rename(columns={"points": "stage_points"})
        )

        final_stage_points = (
            final_results
            .merge(selections, on="rider_id", how="inner")
            .assign(stage_id="final", stage=final_stage_nr)
            .groupby(["stage", "stage_id", "id", "voornaam", "achternaam"], as_index=False)
            ["points"].sum()
            .rename(columns={"points": "stage_points"})
        )

        all_participant_stage_scores = pd.concat(
            [participant_stage_points, final_stage_points], ignore_index=True
        )

        # ── Cross join deelnemers × alle etappes ──────────────────────────────
        all_combinations = (
            stage_info
            .merge(selections[["id", "voornaam", "achternaam"]].drop_duplicates(), how="cross")
        )

        ranked = (
            all_combinations
            .merge(
                all_participant_stage_scores[["stage_id", "id", "stage_points"]],
                on=["stage_id", "id"], how="left"
            )
            .fillna({"stage_points": 0})
            .sort_values(["id", "stage"])
        )
        ranked["cumulative_points"] = ranked.groupby("id")["stage_points"].cumsum()
        ranked = ranked.sort_values(["stage", "cumulative_points"], ascending=[True, False])
        ranked["rank"] = ranked.groupby("stage").cumcount() + 1

        # ── Wegschrijven ──────────────────────────────────────────────────────
        out_dir = BASE_DIR / "data" / "processed" / "ranking"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"ranking_by_stage_{event_id}_{event_year}.csv"
        ranked.to_csv(out_file, index=False)
        print(f"  Opgeslagen: {out_file} ({len(ranked)} rijen)")
        print(f"=== Klaar: {event_id} {event_year} ===")


if __name__ == "__main__":
    main()
