# scripts/process_favorites.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from scipy.stats.mstats import winsorize
from scipy.stats import zscore

from config import EVENT_YEARS, BASE_DIR

WINSOR_COLS = [
    "pcs_rank", "event_rank", "uci_points", "pcs_points_season",
    "pcs_gc_points_season", "pcs_points_last_60d",
    "pcs_gc_points", "pcs_sprint_points", "pcs_sprint_points_season",
]

# Events die de GT-specifieke scoring gebruiken.
# Originele berekening (classic_score) blijft beschikbaar als kolom voor vergelijking.
GT_SCORING_EVENTS = {"giro-d-italia"}


def _safe_zscore(series: pd.Series) -> pd.Series:
    """Z-score met fallback naar 0 als standaarddeviatie 0 is."""
    vals = series.to_numpy(dtype=float)
    std  = np.nanstd(vals)
    if std == 0:
        return pd.Series(np.zeros(len(vals)), index=series.index)
    return pd.Series(zscore(vals, nan_policy="omit"), index=series.index)


def compute_favorites(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Winsoriseer per event ─────────────────────────────────────────────────
    def winsor_group(g):
        for col in WINSOR_COLS:
            if col in g.columns:
                vals = g[col].to_numpy(dtype=float)
                g[f"{col}_w"] = np.array(winsorize(vals, limits=[0.01, 0.01]))
        return g

    df = df.groupby(["event_id", "event_date"], group_keys=False).apply(winsor_group)

    # 2. Gecombineerde scores per event ────────────────────────────────────────
    def score_group(g):
        event_id = g["event_id"].iloc[0]
        is_gt    = event_id in GT_SCORING_EVENTS

        def z(col):
            return _safe_zscore(g[f"{col}_w"])

        # gc_score: historische GC-prestaties (gewogen 3 jaar) + huidig seizoen
        g["gc_score"] = (
            -z("pcs_rank") * 0.5
            - z("event_rank") * 0.5
            + z("uci_points") * 0.5
            + z("pcs_gc_points_season") * 1.5
            + z("pcs_gc_points") * 1.5
        )

        # classic_score: originele berekening — altijd aanwezig voor vergelijking
        g["classic_score"] = (
            -z("pcs_rank") * 0.5
            - z("event_rank") * 0.5
            + z("uci_points") * 0.5
            + z("pcs_points_season") * 1.5
            + z("pcs_points_last_60d") * 1.5
        )

        # sprinter_score: vlakke-koersen specialisatie
        g["sprinter_score"] = (
            -z("pcs_rank") * 0.5
            - z("event_rank") * 0.5
            + z("uci_points") * 0.5
            + z("pcs_sprint_points_season") * 1.5
            + z("pcs_sprint_points") * 1.5
        )

        if is_gt:
            # stage_form_score vervangt classic_score voor GT-events.
            # Gebruikt pcs_gc_points_season i.p.v. pcs_points_season zodat sprinters
            # niet onterecht hoog scoren door flat-race seizoenspunten.
            g["stage_form_score"] = (
                -z("pcs_rank") * 0.5
                - z("event_rank") * 0.5
                + z("uci_points") * 0.5
                + z("pcs_gc_points_season") * 1.5   # GC-specifiek, niet alle race-types
                + z("pcs_points_last_60d") * 1.5    # recente vorm (GT-voorbereiding)
            )
            g["combined_score"] = (
                g["gc_score"] * 0.48
                + g["stage_form_score"] * 0.27
                + g["sprinter_score"] * 0.25
            )
        else:
            g["combined_score"] = (
                g["gc_score"] * 0.5
                + g["classic_score"] * 0.3
                + g["sprinter_score"] * 0.2
            )

        return g

    df = df.groupby(["event_id", "event_date"], group_keys=False).apply(score_group)

    # 3. Top 15 rangschikken ───────────────────────────────────────────────────
    df = df.sort_values("combined_score", ascending=False)
    df["rank"] = df.groupby(["event_id", "event_date"]).cumcount() + 1
    df["rank"] = df["rank"].where(df["rank"] <= 15, other=np.nan)

    # 4. Tier-indeling voor top 15 ────────────────────────────────────────────
    def assign_tiers(g):
        top15 = g[g["rank"].notna()].copy().sort_values("combined_score", ascending=False)
        if top15.empty:
            return g

        event_id = g["event_id"].iloc[0]
        is_gt    = event_id in GT_SCORING_EVENTS

        scores = top15["combined_score"].values
        std    = np.nanstd(scores)

        if is_gt:
            # Gap-progressie: tier-grens waar het verschil groter is dan de drempel.
            # Meerdere rijders per tier zijn mogelijk — rank 1 is niet automatisch solo Tier 1.
            gap_threshold = std * 0.8
            current_tier  = 1
            tiers         = [1]
            for i in range(1, len(scores)):
                if scores[i - 1] - scores[i] > gap_threshold:
                    current_tier = min(current_tier + 1, 3)
                tiers.append(current_tier)
        else:
            # Originele logica: rank 1 altijd Tier 1, gap-detectie enkel voor rank ≤ 3
            diff_next = np.append(scores[:-1] - scores[1:], np.nan)
            big_gap   = diff_next > std
            tiers = []
            for i, (rank_val, gap) in enumerate(zip(top15["rank"].values, big_gap)):
                if rank_val == 1:
                    tiers.append(1)
                elif gap and rank_val <= 3:
                    tiers.append(2)
                else:
                    tiers.append(3)

        top15["tier"] = tiers

        # Fallback als niet alle 3 tiers bezet zijn
        if top15["tier"].nunique() < 3:
            q = np.nanpercentile(scores, [33.3, 80])
            top15["tier"] = np.where(
                scores >= q[1], 1,
                np.where(scores >= q[0], 2, 3)
            )

        # Teamregel: max 1 renner per team in Tier 1
        seen_teams = set()
        for idx in top15.index:
            team = top15.at[idx, "team_id"]
            if top15.at[idx, "tier"] == 1:
                if team in seen_teams:
                    top15.at[idx, "tier"] = 2
                else:
                    seen_teams.add(team)

        top15["fav_points"] = top15["tier"].map({1: 6, 2: 3, 3: 1})

        g = g.copy()
        g = g.merge(
            top15[["rider_id", "tier", "fav_points"]],
            on="rider_id", how="left"
        )
        return g

    df = df.groupby(["event_id", "event_date"], group_keys=False).apply(assign_tiers)

    # 5. NA's opvullen met 0 voor niet-favorieten ─────────────────────────────
    for col in ["rank", "tier", "fav_points"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    return df


def main() -> None:
    print("\n=== Processing favorites ===")

    startlist_dir = BASE_DIR / "data" / "processed" / "startlists"
    files = list(startlist_dir.glob("startlist_*.csv"))

    if not files:
        print(f"  [SKIP] Geen startlist bestanden gevonden in {startlist_dir}")
        return

    df = pd.concat(
        [pd.read_csv(f, encoding="utf-8") for f in files],
        ignore_index=True
    )
    df["pcs_rank"]   = pd.to_numeric(df["pcs_rank"],   errors="coerce")
    df["event_rank"] = pd.to_numeric(df["event_rank"], errors="coerce")

    df_enriched = compute_favorites(df)

    out_dir = BASE_DIR / "data" / "processed" / "startlists_favorites"
    out_dir.mkdir(parents=True, exist_ok=True)

    for (event_id, event_date), group in df_enriched.groupby(["event_id", "event_date"]):
        year     = pd.to_datetime(event_date, errors="coerce").year
        out_file = out_dir / f"startlist_{event_id}_{year}.csv"
        group.to_csv(out_file, index=False)
        print(f"  Opgeslagen: {out_file} ({len(group)} renners)")

    print("=== Klaar: favorites ===")


if __name__ == "__main__":
    main()
