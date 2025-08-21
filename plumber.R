# plumber.R
library(plumber)
library(readr)
library(glue)

#* @apiTitle TourManager Scraper API

#* Get startlist
#* @param event_id
#* @param year
#* @get /startlist
function(event_id, year) {
  f <- glue("data/processed/startlists/startlist_{event_id}_{year}.csv")
  if (!file.exists(f)) return(list(error = "Not found"))
  read_csv(f)
}

#* Get stages
#* @param event_id
#* @param year
#* @get /stages
function(event_id, year) {
  f <- glue("data/processed/stages/stages_{event_id}_{year}.csv")
  if (!file.exists(f)) return(list(error = "Not found"))
  read_csv(f)
}

#* Get stage results
#* @param event_id
#* @param year
#* @param category (optional)
#* @param stage_id (optional)
#* @param rider_id (optional)
#* @get /stage_results
function(event_id, year, category = NULL, stage_id = NULL, rider_id = NULL) {
  path <- glue("data/processed/results/{event_id}_{year}_all_stage_results.csv")
  if (!file.exists(path)) return(list(error = "Not found"))
  df <- read_csv(path)
  df <- df %>% filter(
    is.null(category) | category == category,
    is.null(stage_id) | stage_id == stage_id,
    is.null(rider_id) | rider_id == rider_id
  )
  df
}
