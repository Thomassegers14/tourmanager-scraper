# Config en functies
source("config/config.R")
source("R/scrape_stage_results.R")
source("R/scrape_stages.R")

# Parallel plan instellen
if (.Platform$OS.type == "windows") {
  plan(multisession, workers = max(1, parallel::detectCores() - 1))
} else {
  plan(multicore, workers = max(1, parallel::detectCores() - 1))
}

# Safe wrapper zodat future_map niet crasht
safe_scrape <- purrr::possibly(
  .f = function(event_id, year, stage_id, category) {
    df <- scrape_stage_results(event_id, year, stage_id, category)
    if (is.null(df)) {
      # altijd een tibble teruggeven
      return(tibble::tibble(
        event_id = character(),
        year = numeric(),
        stage_id = character(),
        category = character(),
        rank = character(),
        rider_id = character()
      ))
    }
    df
  },
  otherwise = tibble::tibble(
    event_id = character(),
    year = numeric(),
    stage_id = character(),
    category = character(),
    rank = character(),
    rider_id = character()
  )
)

for (i in seq_len(nrow(EVENT_YEARS))) {
  id   <- EVENT_YEARS$event_id[i]
  year <- EVENT_YEARS$event_year[i]

  message(glue("Scraping results: {id} {year}"))

  stages <- scrape_stages(id, year)
  categories <- c("stage", "gc", "points", "kom", "youth")

  stage_cat <- tidyr::crossing(stage_id = stages$stage_id, category = categories)

  all_results <- furrr::future_pmap_dfr(
    list(stage_cat$stage_id, stage_cat$category),
    function(stage_id, category) {
      safe_scrape(event_id = id, year = year, stage_id = stage_id, category = category)
    },
    .options = furrr::furrr_options(seed = TRUE)
  )

  if (nrow(all_results) > 0) {
    dir.create("data/processed/results", showWarnings = FALSE, recursive = TRUE)
    file <- glue("data/processed/results/{id}_{year}_all_stage_results.csv")
    readr::write_csv(all_results, file)
    message(glue("✅ Saved results: {file}"))
  } else {
    message("ℹ No results available yet.")
  }
}
