# scripts/pipeline.py
#
# Voert de volledige pipeline uit in de juiste volgorde.
#
# Gebruik:
#   python scripts/pipeline.py                        → alle stappen
#   python scripts/pipeline.py scrape_startlists      → één stap
#   python scripts/pipeline.py scrape_stages process_favorites → selectie
#
# Stappen en hun volgorde:
#   1. scrape_startlists   — renners, kwaliteit, rijdervorm scrapen
#   2. scrape_stages       — etappeinfo scrapen
#   3. scrape_results      — etapperesultaten scrapen (vereist: stages)
#   4. process_results     — parquet → CSV consolideren (vereist: scrape_results)
#   5. process_favorites   — favorieten berekenen (vereist: scrape_startlists)
#   6. process_selections  — deelnemerskeuzes uit database ophalen
#   7. compute_scores      — deelnemersklassement (vereist: stap 4, 5, 6)
#   8. compute_rider_points — rennerssamenvatting (vereist: stap 4, 5)

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import traceback

from run_scrape_startlists import main as scrape_startlists
from run_scrape_stages      import main as scrape_stages
from run_scrape_results     import main as scrape_results
from process_stage_results  import main as process_results
from process_favorites      import main as process_favorites
from process_selections     import main as process_selections
from compute_scores         import main as compute_scores
from compute_rider_points   import main as compute_rider_points

STEPS: list[tuple[str, callable]] = [
    ("scrape_startlists",    scrape_startlists),
    ("scrape_stages",        scrape_stages),
    ("scrape_results",       scrape_results),
    ("process_results",      process_results),
    ("process_favorites",    process_favorites),
    ("process_selections",   process_selections),
    ("compute_scores",       compute_scores),
    ("compute_rider_points", compute_rider_points),
]

STEP_NAMES = [name for name, _ in STEPS]


def run(requested: list[str] | None = None) -> None:
    if requested:
        unknown = set(requested) - set(STEP_NAMES)
        if unknown:
            print(f"[ERROR] Onbekende stappen: {unknown}")
            print(f"Beschikbare stappen: {STEP_NAMES}")
            sys.exit(1)

    errors: list[str] = []

    for name, fn in STEPS:
        if requested and name not in requested:
            continue

        print(f"\n{'=' * 60}")
        print(f"STAP: {name}")
        print(f"{'=' * 60}")

        try:
            fn()
        except Exception:
            print(f"\n[ERROR] Stap '{name}' mislukt:")
            traceback.print_exc()
            errors.append(name)

    print(f"\n{'=' * 60}")
    if errors:
        print(f"Pipeline klaar met fouten in: {errors}")
        sys.exit(1)
    else:
        print("Pipeline succesvol afgerond.")


if __name__ == "__main__":
    requested = sys.argv[1:] or None
    run(requested)
