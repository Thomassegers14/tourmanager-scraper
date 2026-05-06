# scripts/run_scrape_results.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from config import EVENT_YEARS, BASE_URL, BASE_DIR, CATEGORIES
from utils import read_page
from run_scrape_stages import scrape_stages

EMPTY_DF = pd.DataFrame(columns=["event_id", "year", "stage_id", "category", "rank", "rider_id"])


def _stage_date(stage_id: str) -> date | None:
    """Haal de etappedatum op van PCS. Geeft None terug bij fout."""
    try:
        soup = read_page(f"{BASE_URL}/{stage_id}")
        li   = soup.select_one(".keyvalueList li")
        if li is None:
            return None
        text = li.get_text(strip=True).replace("Date:", "").strip()
        return pd.to_datetime(text, dayfirst=True, errors="coerce").date()
    except Exception:
        return None


def _build_url(event_id: str, year: int, stage_id: str, category: str, is_last_stage: bool) -> str:
    if category == "stage":
        return f"{BASE_URL}/{stage_id}/result/result"
    if is_last_stage:
        if year <= 2023 and category != "gc":
            return f"{BASE_URL}/race/{event_id}/{year}/stage-21-{category}"
        return f"{BASE_URL}/race/{event_id}/{year}/{category}"
    return f"{BASE_URL}/{stage_id}-{category}"


def scrape_stage_results(
    event_id: str, year: int, stage_id: str,
    category: str, is_last_stage: bool = False
) -> pd.DataFrame:
    url = _build_url(event_id, year, stage_id, category, is_last_stage)

    try:
        page = read_page(url)
    except Exception:
        return EMPTY_DF.copy()

    # Etappedatum controleren — sla over als nog niet gereden
    stage_dt = _stage_date(stage_id)
    if stage_dt is None or stage_dt > date.today():
        print(f"  [SKIP] {stage_id} ({category}) nog niet gereden")
        return EMPTY_DF.copy()

    # ── TTT ──────────────────────────────────────────────────────────────────
    ttt_list = page.select("ul.ttt-results")
    if ttt_list and category == "stage":
        teams = ttt_list[0].find_all("li")
        rows  = []
        for rank_0, team in enumerate(teams):
            for tr in team.find_all("tr"):
                a = tr.select_one("a[href*='rider']")
                if a:
                    rows.append({
                        "event_id": str(event_id),
                        "year":     int(year),
                        "stage_id": str(stage_id),
                        "category": str(category),
                        "rank":     str(rank_0),
                        "rider_id": a.get("href"),
                    })
        return pd.DataFrame(rows) if rows else EMPTY_DF.copy()

    # ── Normale resultaten ────────────────────────────────────────────────────
    res_tabs = [t for t in page.select("div.resTab") if "hide" not in t.get("class", [])]
    if not res_tabs:
        return EMPTY_DF.copy()

    results_el = res_tabs[0].select_one(".results")
    if results_el is None:
        return EMPTY_DF.copy()

    try:
        results_df = pd.read_html(StringIO(str(results_el)), convert_float=False)[0]
    except Exception:
        return EMPTY_DF.copy()

    if results_df.empty:
        return EMPTY_DF.copy()

    rank_col = results_df.columns[0]
    results_df = results_df[[rank_col]].rename(columns={rank_col: "rank"})
    results_df = results_df[~results_df["rank"].astype(str).str.contains("relegated", case=False)]

    rider_ids = [
        a.get("href") for a in res_tabs[0].select("a")
        if "rider" in (a.get("href") or "")
    ]

    n = min(len(results_df), len(rider_ids))
    if n == 0:
        return EMPTY_DF.copy()

    return pd.DataFrame({
        "event_id": str(event_id),
        "year":     int(year),
        "stage_id": str(stage_id),
        "category": str(category),
        "rank":     results_df["rank"].iloc[:n].astype(str).values,
        "rider_id": rider_ids[:n],
    })


def safe_scrape(
    event_id: str, year: int, stage_id: str,
    category: str, is_last_stage: bool = False,
    max_retries: int = 3
) -> pd.DataFrame:
    for attempt in range(max_retries):
        try:
            result = scrape_stage_results(event_id, year, stage_id, category, is_last_stage)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  [ERROR] {stage_id} {category} mislukt na {max_retries} pogingen: {e}")
                return EMPTY_DF.copy()
    return EMPTY_DF.copy()


def main() -> None:
    for ev in EVENT_YEARS:
        event_id   = ev["event_id"]
        event_year = ev["event_year"]

        print(f"\n=== Scraping results: {event_id} {event_year} ===")

        stages = scrape_stages(event_id, event_year)
        last_stage_id = stages.loc[stages["stage"] == stages["stage"].max(), "stage_id"].iloc[0]

        tasks = [
            (str(row.stage_id), cat, row.stage_id == last_stage_id, int(row.stage))
            for _, row in stages.iterrows()
            for cat in CATEGORIES
        ]

        def process(task):
            stage_id, category, is_last, stage_nr = task
            df = safe_scrape(event_id, event_year, stage_id, category, is_last)
            if df.empty:
                return

            # Sorteren
            cat_order = {c: i for i, c in enumerate(CATEGORIES)}
            df["_rank_num"] = pd.to_numeric(df["rank"], errors="coerce")
            df["_cat_ord"]  = df["category"].map(cat_order)
            df = df.sort_values(["_cat_ord", "_rank_num", "rider_id"]).drop(columns=["_rank_num", "_cat_ord"])

            # Wegschrijven als parquet
            out_dir = BASE_DIR / "data" / "raw" / "results" / event_id / str(event_year)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"stage-{stage_nr}-{category}.parquet"

            # Alleen overschrijven als inhoud verschilt
            if out_file.exists():
                old = pd.read_parquet(out_file)
                if old.equals(df.reset_index(drop=True)):
                    print(f"  [=] Ongewijzigd: {out_file.name}")
                    return

            df.to_parquet(out_file, index=False)
            print(f"  [+] Opgeslagen: {out_file.name} ({len(df)} rijen)")

        with ThreadPoolExecutor(max_workers=2) as exe:
            futures = {exe.submit(process, t): t for t in tasks}
            for fut in as_completed(futures):
                exc = fut.exception()
                if exc:
                    print(f"  [ERROR] {futures[fut]}: {exc}")

        print(f"=== Klaar: {event_id} {event_year} ===")


if __name__ == "__main__":
    main()
