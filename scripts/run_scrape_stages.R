# Config en functies
source("config/config.R")
source("R/scrape_stages.R")

for (i in seq_len(nrow(EVENT_YEARS))) {
  id <- EVENT_YEARS$event_id[i]
  year <- EVENT_YEARS$event_year[i]

  message(glue("Scraping stages: {id} {year}"))

  stages <- scrape_stages(id, year)

  dir.create("data/processed/stages", showWarnings = FALSE, recursive = TRUE)
  file <- glue("data/processed/stages/stages_{id}_{year}.csv")
  write_csv(stages, file)
  message(glue("Saved stages: {file}"))
}
