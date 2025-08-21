# scripts/run_scrape_startlists.R

# Config en functies
source("config/config.R")
source("R/scrape_startlist.R")
source("R/scrape_startlist_quality.R")
source("R/scrape_rider_form.R")
source("R/scrape_stages.R")

# Loop over events en jaren
for(i in seq_len(nrow(EVENT_YEARS))) {
  
  id   <- EVENT_YEARS$event_id[i]
  year <- EVENT_YEARS$event_year[i]
  
  message(glue::glue("=== Scraping startlist & stages: {id} {year} ==="))
  
  # --- STARTLIST ---
  startlist <- scrape_startlist(id, year)
  quality   <- scrape_startlist_quality(id, year)
  
  form <- scrape_all_rider_forms(
    rider_ids  = startlist$rider_id,
    event_date = as.Date(unique(startlist$event_date)),
    event_year = year
  )
  
  startlist_full <- startlist %>%
    dplyr::left_join(quality, by = "rider_id") %>%
    dplyr::left_join(form,    by = "rider_id")
  
  # Opslaan
  dir.create("data/processed/startlists", showWarnings = FALSE, recursive = TRUE)
  startlist_file <- glue::glue("data/processed/startlists/startlist_{id}_{year}.csv")
  readr::write_csv(startlist_full, startlist_file)
  message(glue::glue("Saved startlist: {startlist_file}"))
  
  # --- STAGES ---
  stages <- scrape_stages(id, year)
  dir.create("data/processed/stages", showWarnings = FALSE, recursive = TRUE)
  stages_file <- glue::glue("data/processed/stages/stages_{id}_{year}.csv")
  readr::write_csv(stages, stages_file)
  message(glue::glue("Saved stages: {stages_file}"))
  
  message(glue::glue("Finished {id} {year}"))
}
