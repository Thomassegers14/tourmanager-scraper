# scripts/run_scrape_startlists.py

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO

from bs4 import BeautifulSoup
import pandas as pd

from config import EVENT_YEARS, BASE_URL, BASE_DIR
from utils import read_page


# ── scrape_startlist ──────────────────────────────────────────────────────────

def scrape_startlist(event_id: str, year: int) -> pd.DataFrame:
    print(f"  Fetching startlist page...")
    page = read_page(f"{BASE_URL}/race/{event_id}/{year}/startlist/startlist")

    print(f"  Fetching event date...")
    event_page = read_page(f"{BASE_URL}/race/{event_id}/{year}")
    event_date = None

    for li in event_page.find_all("li"):
        title_div = li.find("div", class_="title ")
        if title_div and "startdate" in title_div.get_text(strip=True).lower():
            value_div = li.find("div", class_=" value")
            if value_div:
                event_date = value_div.get_text(strip=True)
                break

    if event_date is None:
        for el in event_page.find_all(string=lambda t: t and "startdate" in t.lower()):
            parent = el.find_parent()
            if parent:
                sibling = parent.find_next_sibling()
                if sibling:
                    event_date = sibling.get_text(strip=True)
                    break

    if event_date is None:
        print(f"  [WARN] Startdatum niet gevonden, gebruik fallback")
        event_date = f"01 January {year}"

    print(f"  Gevonden startdatum (raw): {event_date}")

    teams = page.find_all(class_="ridersCont")
    teams_clean = [t for t in teams if t.find_all("li")]

    rows = []
    for team in teams_clean:
        team_a    = team.find(class_="team")
        team_name = team_a.get_text(strip=True) if team_a else None
        team_id   = team_a.get("href")          if team_a else None
        for li in team.find_all("li"):
            a = li.find("a")
            if a:
                rows.append({
                    "event_id":   event_id,
                    "event_date": event_date,
                    "team_name":  team_name,
                    "team_id":    team_id,
                    "rider_name": a.get_text(strip=True),
                    "rider_id":   a.get("href"),
                })

    df = pd.DataFrame(rows)
    print(f"  Startlist: {len(df)} renners, {df['team_name'].nunique()} teams")
    return df


# ── scrape_startlist_quality ──────────────────────────────────────────────────

def scrape_startlist_quality(event_id: str, year: int) -> pd.DataFrame:
    print(f"  Fetching startlist-quality page...")
    page = read_page(f"{BASE_URL}/race/{event_id}/{year}/startlist/startlist-quality")

    table_el = page.find(class_="basic")
    if table_el is None:
        raise ValueError("Kon .basic tabel niet vinden op startlist-quality pagina")

    df = pd.read_html(StringIO(str(table_el)))[0]

    pos_col = next((c for c in df.columns if "pos" in str(c).lower()), None)
    pcs_col = next((c for c in df.columns if "pcs" in str(c).lower()), None)
    if pos_col is None or pcs_col is None:
        raise ValueError(f"Verwachte kolommen niet gevonden. Beschikbaar: {df.columns.tolist()}")

    df = df.dropna(subset=[pos_col])
    rider_ids = [a.get("href") for a in table_el.find_all("a")]

    result = pd.DataFrame({
        "rider_id":   rider_ids[:len(df)],
        "pcs_rank":   df[pcs_col].values,
        "event_rank": df[pos_col].values,
    })
    print(f"  Quality: {len(result)} renners")
    return result


# ── scrape_rider_form ─────────────────────────────────────────────────────────

def _parse_points_table(soup: BeautifulSoup) -> pd.DataFrame:
    table_el = soup.find(class_="basic")
    if table_el is None:
        return pd.DataFrame(columns=["date", "race_name", "pcs_points", "uci_points"])

    df = pd.read_html(StringIO(str(table_el)))[0]
    df = df.rename(columns={
        "Date":       "date",
        "Race":       "race_name",
        "PCS points": "pcs_points",
        "UCI points": "uci_points",
    })
    df["date"]       = pd.to_datetime(df["date"], errors="coerce")
    df["pcs_points"] = pd.to_numeric(df.get("pcs_points"), errors="coerce")
    df["uci_points"] = pd.to_numeric(df.get("uci_points"), errors="coerce")
    return df[df["date"].notna()].copy()


def _weighted_sum(df: pd.DataFrame, event_date: date, col: str) -> float:
    ed = pd.Timestamp(event_date)
    df = df[df["date"] <= ed].copy()

    def weight(d):
        if d <= ed - pd.DateOffset(years=3): return 0.0
        if d <= ed - pd.DateOffset(years=2): return 0.5
        if d <= ed - pd.DateOffset(years=1): return 0.75
        return 1.0

    df["w"] = df["date"].apply(weight)
    return float((df[col].fillna(0) * df["w"]).sum())


def scrape_rider_form(rider_id: str, event_date: date, event_year: int) -> dict:
    soup   = read_page(f"{BASE_URL}/{rider_id}/start")
    php_el = soup.find(id="riderid")
    if php_el is None:
        raise ValueError(f"Geen #riderid gevonden voor {rider_id}")
    php_id = php_el.get("value")

    ed = pd.Timestamp(event_date)

    soup_res = read_page(
        f"{BASE_URL}/rider.php?id={php_id}&p=results&s=&xseason={event_year}&pxseason=equal&sort=date"
    )
    df_res = _parse_points_table(soup_res)
    uci_points          = float(df_res.loc[df_res["date"] <= ed, "uci_points"].sum())
    pcs_points_season   = float(df_res.loc[
        (df_res["date"] <= ed) & (df_res["date"] >= ed - pd.DateOffset(years=1)), "pcs_points"
    ].sum())
    pcs_points_last_60d = float(df_res.loc[
        (df_res["date"] <= ed) & (df_res["date"] >= ed - timedelta(days=60)), "pcs_points"
    ].sum())

    soup_gc = read_page(
        f"{BASE_URL}/rider.php?id={php_id}&p=results&s=&xseason={event_year - 3}"
        f"&pxseason=largerorequal&sort=date&type=4"
    )
    df_gc = _parse_points_table(soup_gc)
    pcs_gc_points        = _weighted_sum(df_gc, event_date, "pcs_points")
    pcs_gc_points_season = float(df_gc.loc[
        (df_gc["date"] <= ed) & (df_gc["date"] >= ed - pd.DateOffset(years=1)), "pcs_points"
    ].sum())

    soup_sp = read_page(
        f"{BASE_URL}/rider.php?id={php_id}&p=results&s=&xseason={event_year - 3}"
        f"&pxseason=largerorequal&km1=100&pkm1=largerorequal"
        f"&sort=date&vert_meters=1500&pvert_meters=smallerorequal"
    )
    df_sp = _parse_points_table(soup_sp)
    pcs_sprint_points        = _weighted_sum(df_sp, event_date, "pcs_points")
    pcs_sprint_points_season = float(df_sp.loc[
        (df_sp["date"] <= ed) & (df_sp["date"] >= ed - pd.DateOffset(years=1)), "pcs_points"
    ].sum())

    return {
        "rider_id":                 rider_id,
        "uci_points":               uci_points,
        "pcs_points_season":        pcs_points_season,
        "pcs_points_last_60d":      pcs_points_last_60d,
        "pcs_gc_points":            pcs_gc_points,
        "pcs_gc_points_season":     pcs_gc_points_season,
        "pcs_sprint_points":        pcs_sprint_points,
        "pcs_sprint_points_season": pcs_sprint_points_season,
    }


def safe_scrape_rider_form(rider_id: str, event_date: date, event_year: int) -> dict:
    try:
        return scrape_rider_form(rider_id, event_date, event_year)
    except Exception as e:
        print(f"  [WARN] Form mislukt voor {rider_id}: {e}")
        return {
            "rider_id": rider_id,
            "uci_points": None, "pcs_points_season": None,
            "pcs_points_last_60d": None, "pcs_gc_points": None,
            "pcs_gc_points_season": None, "pcs_sprint_points": None,
            "pcs_sprint_points_season": None,
        }


def scrape_all_rider_forms(
    rider_ids: list, event_date: date, event_year: int, workers: int = 4
) -> pd.DataFrame:
    results = []
    total   = len(rider_ids)
    with ThreadPoolExecutor(max_workers=workers) as exe:
        futures = {
            exe.submit(safe_scrape_rider_form, rid, event_date, event_year): rid
            for rid in rider_ids
        }
        for i, fut in enumerate(as_completed(futures), 1):
            print(f"  Form {i}/{total}: {futures[fut]}")
            results.append(fut.result())
    return pd.DataFrame(results)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    for ev in EVENT_YEARS:
        event_id   = ev["event_id"]
        event_year = ev["event_year"]

        print(f"\n=== Scraping startlist: {event_id} {event_year} ===")

        startlist = scrape_startlist(event_id, event_year)
        quality   = scrape_startlist_quality(event_id, event_year)

        event_date = pd.to_datetime(startlist["event_date"].iloc[0], errors="coerce").date()
        if pd.isnull(event_date):
            print(f"  [WARN] Kon startdatum niet parsen, gebruik 1 mei {event_year}")
            event_date = date(event_year, 5, 1)
        print(f"  Startdatum: {event_date}")

        form = scrape_all_rider_forms(
            rider_ids  = startlist["rider_id"].tolist(),
            event_date = event_date,
            event_year = event_year,
        )

        startlist_full = (
            startlist
            .merge(quality, on="rider_id", how="left")
            .merge(form,    on="rider_id", how="left")
        )

        out_dir = BASE_DIR / "data" / "processed" / "startlists"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"startlist_{event_id}_{event_year}.csv"
        startlist_full.to_csv(out_file, index=False)
        print(f"  Opgeslagen: {out_file} ({len(startlist_full)} rijen)")
        print(f"=== Klaar: {event_id} {event_year} ===")


if __name__ == "__main__":
    main()
