# scripts/utils.py — gedeelde HTTP-utilities voor de hele pipeline

import time
import random
from curl_cffi import requests
from curl_cffi.requests.exceptions import HTTPError, RequestException
from bs4 import BeautifulSoup
from config import BASE_URL, HEADERS

# Chrome-varianten om te roteren bij blokkades — elke heeft een eigen TLS/JA3-
# fingerprint, wat de kans verkleint dat Cloudflare ons als bot blijft markeren.
_IMPERSONATE_TARGETS = ["chrome", "chrome131", "chrome124"]

# Statuscodes die we als tijdelijk beschouwen en opnieuw proberen
_RETRY_STATUS = {403, 429, 500, 502, 503, 504}

_MAX_ATTEMPTS = 4


def _new_session(impersonate: str) -> requests.Session:
    s = requests.Session(impersonate=impersonate)
    s.headers.update(HEADERS)
    return s


# Eén sessie voor het hele process — bewaart cookies en hergebruikt TLS-verbinding
_session = _new_session(_IMPERSONATE_TARGETS[0])


def read_page(url: str) -> BeautifulSoup:
    """GET url met random vertraging en retry/backoff, geeft BeautifulSoup terug.

    Bij tijdelijke fouten (403/429/5xx) proberen we het opnieuw met oplopende
    wachttijd en een geroteerde Chrome-fingerprint, omdat Cloudflare vanaf
    datacenter-IP's (GitHub Actions) regelmatig een eerste request blokkeert.
    """
    global _session
    last_exc: Exception | None = None

    for attempt in range(_MAX_ATTEMPTS):
        time.sleep(random.uniform(0.5, 1.5))
        try:
            resp = _session.get(url, timeout=30)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except (HTTPError, RequestException) as exc:
            last_exc = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            # Niet-tijdelijke HTTP-fouten (bv. 404) meteen doorgooien
            if status is not None and status not in _RETRY_STATUS:
                raise
            if attempt < _MAX_ATTEMPTS - 1:
                # Roteer fingerprint en wacht exponentieel langer
                target = _IMPERSONATE_TARGETS[(attempt + 1) % len(_IMPERSONATE_TARGETS)]
                _session = _new_session(target)
                backoff = 2 ** attempt + random.uniform(0, 1)
                time.sleep(backoff)

    raise last_exc


def pcs_url(*parts: str) -> str:
    """Bouw een procyclingstats.com URL van padonderdelen."""
    return BASE_URL + "/" + "/".join(p.strip("/") for p in parts)
