# tourmanager-scraper

Scrapet startlijsten, etappes en resultaten van [procyclingstats.com](https://www.procyclingstats.com)
en verwerkt ze tot de databestanden in `data/processed/`. De pipeline draait via
GitHub Actions (`.github/workflows/`).

## Pipeline draaien

```bash
python scripts/pipeline.py scrape_startlists scrape_stages process_favorites
```

## Cloudflare 403 op GitHub Actions — proxy instellen

procyclingstats.com zit achter Cloudflare. Dat blokkeert datacenter-IP's (zoals
die van GitHub Actions-runners) op IP-reputatie: dezelfde code geeft lokaal `200`
maar vanaf de runner een `HTTP Error 403`. Méér retries of andere browser-fingerprints
helpen niet — alle requests komen van hetzelfde geblokkeerde IP.

De oplossing is requests via een **residentieel IP** routeren met een proxy. De
scraper leest daarvoor de env var `SCRAPER_PROXY`:

- **Niet gezet** → directe verbinding (ongewijzigd gedrag, prima lokaal).
- **Gezet** → alle requests gaan via de opgegeven proxy.

Formaat: `http://gebruiker:wachtwoord@host:poort`

### Op GitHub instellen

1. Neem een (roterende) residentiële proxy. Provider-neutraal — elke proxy met
   bovenstaand URL-formaat werkt (bijv. een goedkope residential/rotating proxy).
2. Repo → **Settings → Secrets and variables → Actions → New repository secret**.
3. Naam: `SCRAPER_PROXY`, waarde: de volledige proxy-URL.

De workflows (`main.yml` en `startlist-check.yml`) geven dit secret al door als
`SCRAPER_PROXY`. In de Actions-log verschijnt enkel de proxy-host (zonder
inloggegevens) ter controle.

### Lokaal testen

```bash
SCRAPER_PROXY="http://user:pass@host:port" python scripts/pipeline.py scrape_startlists
```
