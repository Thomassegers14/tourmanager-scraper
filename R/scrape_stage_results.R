scrape_stage_results <- function(event_id, year, stage_id, category) {
  options(timeout = 800)
  
  # URL bepalen
  url <- if (category == "stage") {
    glue::glue("https://www.procyclingstats.com/{stage_id}/result/result")
  } else if (stage_id == last(stages$stage_id)) {
    if (year <= 2023 & category != "gc") {
      glue::glue("https://www.procyclingstats.com/race/{event_id}/{year}/stage-21-{category}")
    } else {
      glue::glue("https://www.procyclingstats.com/race/{event_id}/{year}/{category}")
    }
  } else {
    glue::glue("https://www.procyclingstats.com/{stage_id}-{category}")
  }
  
  message(glue::glue("Fetching: {url}"))
  
  # HTML laden
  page <- tryCatch(read_html(url),
                   error = function(e) {
                     message(glue::glue("Could not fetch {url}: {e$message}"))
                     return(NULL)
                   })
  if (is.null(page)) return(NULL)
  
  # Zoek resultaten-tabel
  tables <- page %>% html_elements("div:not(.hide).resTab") %>% html_element(".results")
  
  if (length(tables) == 0 || is.na(tables)) {
    message(glue::glue("⚠️ No results table found for {stage_id} ({category}). Skipping."))
    return(NULL)
  }
  
  # Stage datum ophalen
  stage_page <- tryCatch(read_html(glue::glue("https://www.procyclingstats.com/{stage_id}")),
                         error = function(e) {
                           message(glue::glue("Could not fetch stage page {stage_id}: {e$message}"))
                           return(NULL)
                         })
  if (is.null(stage_page)) return(NULL)
  
  stageDate <- stage_page %>% html_element(".keyvalueList") %>% html_element("li") %>% html_text()
  stageDate <- lubridate::dmy(trimws(gsub("Date: ","", stageDate)), locale = "C")
  
  if (is.na(stageDate) || stageDate > Sys.Date()) {
    message(glue::glue("Stage {stage_id} ({category}) has not been run yet. Skipping."))
    return(NULL)
  }
  
  # Resultaten verwerken
  results_df <- tables %>%
    html_table(convert = FALSE) %>%
    as.data.frame() %>%
    select(rank = 1) %>%
    filter(!grepl("relegated", rank))
  
  rider_ids <- tables %>%
    html_elements("a") %>%
    html_attr("href") %>%
    str_subset("rider/")
  
  df <- data.frame(
    event_id = event_id,
    year = year,
    stage_id = stage_id,
    category = category,
    rank = results_df$rank,
    rider_id = rider_ids,
    stringsAsFactors = FALSE
  )
  
  return(df)
}
