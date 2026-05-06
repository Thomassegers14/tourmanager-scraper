# scripts/utils.py — gedeelde HTTP-utilities voor de hele pipeline

import time
import random
from curl_cffi import requests
from bs4 import BeautifulSoup
from config import BASE_URL, HEADERS

# Eén sessie voor het hele process — bewaart cookies en hergebruikt TLS-verbinding
_session = requests.Session(impersonate="chrome")
_session.headers.update(HEADERS)


def read_page(url: str) -> BeautifulSoup:
    """GET url met random vertraging, geeft geparsede BeautifulSoup terug."""
    time.sleep(random.uniform(0.5, 1.5))
    resp = _session.get(url, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def pcs_url(*parts: str) -> str:
    """Bouw een procyclingstats.com URL van padonderdelen."""
    return BASE_URL + "/" + "/".join(p.strip("/") for p in parts)
