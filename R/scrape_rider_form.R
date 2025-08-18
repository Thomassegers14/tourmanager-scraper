# R/scrape_rider_form.R
scrape_rider_form <- function(rider_id, event_date, event_year) {
  library(rvest)
  library(dplyr)
  library(glue)

  # Scrape rider PHP ID
  rider_php_id <- read_html(glue("https://www.procyclingstats.com/{rider_id}/start")) %>%
    html_element("#riderid") %>%
    html_attr("value")

  # Build PCS results URL
  url <- glue(
    "https://www.procyclingstats.com/rider.php?id={rider_php_id}&p=results&s=&xseason={event_year}&pxseason=equal&sort=date"
  )

  # Scrape rider results
  rider_points <- read_html(url) %>%
    html_element(".basic") %>%
    html_table() %>%
    transmute(
      date       = as.Date(Date),
      race_name  = Race,
      pcs_points = suppressWarnings(as.numeric(`PCS points`)),
      uci_points = suppressWarnings(as.numeric(`UCI points`))
    ) %>%
    filter(!is.na(date)) %>%
    summarise(
      uci_points          = sum(uci_points, na.rm = TRUE),
      pcs_points_season   = sum(pcs_points[date <= event_date], na.rm = TRUE),
      pcs_gc_points       = sum(pcs_points[grepl("General classification", race_name)], na.rm = TRUE),
      pcs_points_last_60d = sum(pcs_points[date <= event_date & date >= event_date - 60], na.rm = TRUE)
    )

  # Return dataframe
  data.frame(rider_id = rider_id, rider_points)
}

# Safe wrapper to catch errors and return NA row
safe_scrape_rider_form <- purrr::possibly(
  .f = scrape_rider_form,
  otherwise = data.frame(
    rider_id = NA,
    uci_points = NA,
    pcs_points_season = NA,
    pcs_gc_points = NA,
    pcs_points_last_60d = NA
  )
)

# Parallel scraping over all riders
scrape_all_rider_forms <- function(rider_ids, event_date, event_year, workers = parallel::detectCores() - 1) {
  library(furrr)
  plan(multisession, workers = workers)

  furrr::future_map_dfr(
    rider_ids,
    ~ safe_scrape_rider_form(.x, event_date, event_year),
    .progress = TRUE
  )
}
