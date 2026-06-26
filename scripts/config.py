# scripts/config.py — gedeelde configuratie voor de hele pipeline

from pathlib import Path

# Root van de scraper/ directory (één niveau boven scripts/)
BASE_DIR: Path = Path(__file__).parent.parent

BASE_URL: str = "https://www.procyclingstats.com"

EVENT_YEARS: list[dict] = [
    {"event_id": "tour-de-france", "event_year": 2026},
]

HEADERS: dict = {
    "User-Agent":                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language":           "nl-BE,nl;q=0.9,en;q=0.8",
    "Accept-Encoding":           "gzip, deflate, br",
    "Connection":                "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest":            "document",
    "Sec-Fetch-Mode":            "navigate",
    "Sec-Fetch-Site":            "none",
    "Sec-Fetch-User":            "?1",
}

# ── Puntensysteem (vervangt R/point_system.R) ────────────────────────────────

STAGE_POINTS: dict[int, int] = {
    1: 30, 2: 25, 3: 20, 4: 14, 5: 12,
    6: 10, 7:  8, 8:  6, 9:  4, 10: 2,
}

STAGE_POINTS_TTT: dict[int, int] = {k: round(v / 2) for k, v in STAGE_POINTS.items()}

DAILY_CLASS_POINTS: dict[tuple[str, int], int] = {
    ("gc",     1): 5, ("gc",     2): 3, ("gc",     3): 2,
    ("kom",    1): 3, ("kom",    2): 2, ("kom",    3): 1,
    ("points", 1): 3, ("points", 2): 2, ("points", 3): 1,
    ("youth",  1): 3, ("youth",  2): 2, ("youth",  3): 1,
}

_gc_pts    = [90, 80, 75, 70, 65, 60, 55, 50, 45, 40, 38, 36, 34, 32, 30, 28, 26, 24, 22, 20]
_other_pts = [40, 30, 20, 15, 10]

FINAL_CLASS_POINTS: dict[tuple[str, int], int] = {
    **{("gc",     r + 1): p for r, p in enumerate(_gc_pts)},
    **{("kom",    r + 1): p for r, p in enumerate(_other_pts)},
    **{("points", r + 1): p for r, p in enumerate(_other_pts)},
    **{("youth",  r + 1): p for r, p in enumerate(_other_pts)},
}

CATEGORIES: list[str] = ["stage", "gc", "points", "kom", "youth"]
