# R/scrape_startlist.R
scrape_startlist <- function(id, year) {
  library(rvest)
  library(dplyr)
  library(glue)
  library(purrr)

  # Scrape startlist page
  page <- read_html(glue("https://www.procyclingstats.com/race/{id}/{year}/startlist/startlist"))

  # Scrape event date
  event_date <- read_html(glue("https://www.procyclingstats.com/race/{id}/{year}")) %>%
    html_element(xpath = "//li[div[@class='title ' and text()='Startdate: ']]/div[@class=' value']") %>%
    html_text()

  # Get all teams containers
  teams <- page %>% html_elements(".ridersCont")

  # Remove empty team blocks
  teams_clean <- teams[map_lgl(teams, ~ length(html_elements(.x, "li")) > 0)]

  # Build dataframe
  df <- map_df(seq_along(teams_clean), function(i) {
    data.frame(
      event_id    = id,
      event_date  = event_date,
      team_name   = teams_clean[[i]] %>% html_element(".team") %>% html_text(),
      team_id     = teams_clean[[i]] %>% html_element(".team") %>% html_attr("href"),
      rider_name  = teams_clean[[i]] %>% html_elements("li") %>% html_element("a") %>% html_text(),
      rider_id    = teams_clean[[i]] %>% html_elements("li") %>% html_element("a") %>% html_attr("href")
    )
  })

  return(df)
}
