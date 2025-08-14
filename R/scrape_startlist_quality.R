# R/scrape_startlist_quality.R
scrape_startlist_quality <- function(id, year) {
  library(rvest)
  library(dplyr)
  library(glue)

  page <- read_html(glue("https://www.procyclingstats.com/race/{id}/{year}/startlist/startlist-quality"))

  table <- page %>% html_elements(".basic")
  table_data <- table %>%
    html_table() %>%
    as.data.frame() %>%
    filter(!is.na(Pos.))

  rider_ids <- table %>%
    html_elements("a") %>%
    html_attr("href")

  df <- data.frame(
    rider_id   = rider_ids,
    pcs_rank   = table_data$PCS.Ranking,
    event_rank = table_data$Pos.
  )

  return(df)
}
