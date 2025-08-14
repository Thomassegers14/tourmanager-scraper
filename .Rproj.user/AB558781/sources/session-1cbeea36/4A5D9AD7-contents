# Config en functies
source("config/config.R")
source("R/scrape_startlist.R")
source("R/scrape_startlist_quality.R")
source("R/scrape_rider_form.R")
source("R/scrape_stages.R")
source("R/scrape_stage_results.R")

# Parallel plan instellen
# Detecteer OS
if (.Platform$OS.type == "windows") {
  plan(multisession, workers = parallel::detectCores() - 1)
} else {
  plan(multicore, workers = parallel::detectCores() - 1)
}

# Loop over events en jaren
for(i in seq_len(nrow(EVENT_YEARS))) {
  
  id <- EVENT_YEARS$event_id[i]
  year <- EVENT_YEARS$event_year[i]
  
  message(glue("Scraping event: {id} {year}"))
  
  # --- STARTLIST ---
  startlist <- scrape_startlist(id, year)
  quality <- scrape_startlist_quality(id, year)
  
  form <- scrape_all_rider_forms(
    rider_ids  = startlist$rider_id,
    event_date = as.Date(unique(startlist$event_date)),
    event_year = year
  )
  
  startlist_full <- startlist %>%
    left_join(quality, by = "rider_id") %>%
    left_join(form, by = "rider_id")
  
  # Opslaan
  dir.create("data/processed/startlists", showWarnings = FALSE, recursive = TRUE)
  startlist_file <- glue("data/processed/startlists/startlist_{id}_{year}.csv")
  write_csv(startlist_full, startlist_file)
  message(glue("Saved startlist: {startlist_file}"))
  
  # --- STAGES ---
  stages <- scrape_stages(id, year)
  dir.create("data/processed/stages", showWarnings = FALSE, recursive = TRUE)
  stages_file <- glue("data/processed/stages/stages_{id}_{year}.csv")
  write_csv(stages, stages_file)
  message(glue("Saved stages: {stages_file}"))
  
  # --- STAGE RESULTS (parallel) ---
  categories <- c("stage", "gc", "points", "kom", "youth")
  
  stage_cat <- tidyr::crossing(stage_id = stages$stage_id, category = categories)
  
  message("Scraping stage results in parallel...")
  
  all_results <- future_pmap_dfr(
    list(stage_cat$stage_id, stage_cat$category),
    function(stage_id, category) {
      scrape_stage_results(event_id = id, year = year, stage_id = stage_id, category = category)
    },
    .options = furrr_options(seed = TRUE)
  )
  
  # Opslaan in 1 CSV per event/jaar
  if(nrow(all_results) > 0) {
    dir.create("data/processed/results", showWarnings = FALSE, recursive = TRUE)
    results_file <- glue("data/processed/results/{id}_{year}_all_stage_results.csv")
    write_csv(all_results, results_file)
    message(glue("Saved all stage results: {results_file}"))
  } else {
    message("No stage results available yet.")
  }
  
  message(glue("Finished scraping {id} {year}"))
}
