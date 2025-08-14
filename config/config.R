# config.R

# List of events to scrape
EVENT_YEARS <- tidyr::crossing(
  event_id   = c("vuelta-a-espana", "tour-de-france", "giro-d-italia"),
  event_year = c(2024, 2025)
)

BASE_URL <- "https://www.procyclingstats.com"
USER_AGENT <- "Mozilla/5.0 (Windows NT 10.0; Win64; x64) R Scraper"

library(rvest)
library(dplyr)
library(stringr)
library(purrr)
library(tidyr)
library(furrr)
library(glue)
library(readr)

# Helper om pagina's te laden met user-agent
read_page <- function(url) {
  Sys.sleep(runif(1, 0.5, 1.5)) # random delay om ban te vermijden
  read_html(httr::GET(url, httr::add_headers("User-Agent" = USER_AGENT)))
}

# Zet de parallel backend op (bijv. alle cores behalve 1)
plan(multisession, workers = parallel::detectCores() - 1)
