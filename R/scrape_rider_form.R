# R/scrape_rider_form.R
scrape_rider_form <- function(rider_id, event_date, event_year) {

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
      uci_points            = sum(uci_points, na.rm = TRUE),
      pcs_points_season     = sum(pcs_points[date <= event_date & date >= event_date - years(1)], na.rm = TRUE),
      pcs_points_last_60d   = sum(pcs_points[date <= event_date & date >= event_date - 60], na.rm = TRUE)
    )

    

  # Scrape gc results
  rider_gc_points <- read_html(glue("https://www.procyclingstats.com/rider.php?id={rider_php_id}&p=results&s=&xseason={event_year - 3}&pxseason=largerorequal&sort=date&type=4")) %>%
    html_element(".basic") %>%
    html_table() %>%
    transmute(
      date       = as.Date(Date),
      race_name  = Race,
      pcs_points = suppressWarnings(as.numeric(`PCS points`)),
    ) %>%
    filter(!is.na(date) & date <= event_date) %>%
    summarise(
      pcs_gc_points = sum(
        case_when(
          date <= event_date - years(3) ~ 0,
          date <= event_date - years(2) ~ pcs_points * 0.5,
          date <= event_date - years(1) ~ pcs_points * 0.75,
          TRUE ~ pcs_points
          ),
        na.rm = T
      ),
      pcs_gc_points_season = sum(pcs_points[date <= event_date & date >= event_date - years(1)], na.rm = TRUE)
    )

    # Scrape sprint results
    rider_sprint_points <- read_html(glue("https://www.procyclingstats.com/rider.php?id={rider_php_id}&p=results&s=&xseason={event_year - 3}&pxseason=largerorequal&km1=100&pkm1=largerorequal&sort=date&vert_meters=1500&pvert_meters=smallerorequal")) %>%
      html_element(".basic") %>%
      html_table() %>%
      transmute(
        date       = as.Date(Date),
        race_name  = Race,
        pcs_points = suppressWarnings(as.numeric(`PCS points`)),
      ) %>%
      filter(!is.na(date) & date < event_date) %>%
      summarise(
        pcs_sprint_points = sum(
          case_when(
            date <= event_date - years(3) ~ 0,
            date <= event_date - years(2) ~ pcs_points * 0.5,
            date <= event_date - years(1) ~ pcs_points * 0.75,
            TRUE ~ pcs_points
            ),
          na.rm = T
        ),
        pcs_sprint_points_season = sum(pcs_points[date <= event_date & date >= event_date - years(1)], na.rm = TRUE)
      )

  # Return dataframe
  data.frame(rider_id = rider_id, rider_points, rider_gc_points, rider_sprint_points)
}

# Safe wrapper to catch errors and return NA row
safe_scrape_rider_form <- purrr::possibly(
  .f = scrape_rider_form,
  otherwise = data.frame(
    rider_id = NA,
    uci_points = NA,
    pcs_points_season = NA,
    pcs_points_last_60d = NA,
    pcs_gc_points = NA,
    pcs_gc_points_season = NA,
    pcs_sprint_points = NA,
    pcs_sprint_points_season = NA
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
