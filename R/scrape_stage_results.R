scrape_stage_results <- function(event_id, year, stage_id, category, is_last_stage = FALSE) {
  options(timeout = 800)

  # URL bepalen
  url <- if (category == "stage") {
    glue("https://www.procyclingstats.com/{stage_id}/result/result")
  } else if (is_last_stage) {
    if (year <= 2023 && category != "gc") {
      glue("https://www.procyclingstats.com/race/{event_id}/{year}/stage-21-{category}")
    } else {
      glue("https://www.procyclingstats.com/race/{event_id}/{year}/{category}")
    }
  } else {
    glue("https://www.procyclingstats.com/{stage_id}-{category}")
  }

  # HTML laden
  page <- tryCatch(read_html(url), error = function(e) {
    return(NULL)
  })
  if (is.null(page)) return(tibble(
    event_id = character(),
    year = numeric(),
    stage_id = character(),
    category = character(),
    rank = character(),
    rider_id = character()
  ))

  # Controleer op TTT
  ttt_list <- html_elements(page, "ul.ttt-results")
  is_ttt <- length(ttt_list) > 0 && category == "stage"

  if (is_ttt) {
    teams <- ttt_list %>% html_elements("li")
    if (length(teams) == 0) {
      return(tibble(
        event_id = character(),
        year = numeric(),
        stage_id = character(),
        category = character(),
        rank = character(),
        rider_id = character()
      ))
    }

    df_ttt <- map_df(seq_along(teams), function(i) {
      team <- teams[[i]]
      rows <- team %>% html_elements("tr")
      if (length(rows) == 0) return(NULL)

      rider_ids <- map_chr(rows, ~ .x %>% html_element("a[href*='rider']") %>% html_attr("href"))
      tibble(
        event_id = as.character(event_id),
        year = as.integer(year),
        stage_id = as.character(stage_id),
        category = as.character(category),
        rank = as.character(i - 1),
        rider_id = rider_ids
      )
    })

    return(df_ttt)
  }

  # Normale resultaten
  tables <- page %>% html_elements("div:not(.hide).resTab") %>% html_element(".results")
  if (length(tables) == 0 || is.na(tables)) {
    return(tibble(
      event_id = character(),
      year = numeric(),
      stage_id = character(),
      category = character(),
      rank = character(),
      rider_id = character()
    ))
  }

  # Stage datum ophalen
  stage_page <- tryCatch(read_html(glue("https://www.procyclingstats.com/{stage_id}")),
                         error = function(e) {
                           return(NULL)
                         })
  if (is.null(stage_page)) return(tibble(
    event_id = character(),
    year = numeric(),
    stage_id = character(),
    category = character(),
    rank = character(),
    rider_id = character()
  ))

  stageDate <- stage_page %>% html_element(".keyvalueList li") %>% html_text()
  stageDate <- lubridate::dmy(trimws(gsub("Date: ", "", stageDate)), locale = "C")

  if (is.na(stageDate) || stageDate > Sys.Date()) {
    message(glue("ℹ️ Stage {stage_id} ({category}) has not been run yet. Skipping."))
    return(tibble(
      event_id = character(),
      year = numeric(),
      stage_id = character(),
      category = character(),
      rank = character(),
      rider_id = character()
    ))
  }

  # Resultaten tabel verwerken
  results_list <- tables %>% html_table(convert = FALSE)
  if (length(results_list) == 0 || nrow(results_list[[1]]) == 0) {
    return(tibble(
      event_id = character(),
      year = numeric(),
      stage_id = character(),
      category = character(),
      rank = character(),
      rider_id = character()
    ))
  }

  results_df <- results_list[[1]] %>% as.data.frame()
  if (ncol(results_df) < 1) {
    return(tibble(
      event_id = character(),
      year = numeric(),
      stage_id = character(),
      category = character(),
      rank = character(),
      rider_id = character()
    ))
  }

  results_df <- results_df %>% select(rank = 1) %>% filter(!grepl("relegated", rank))
  rider_ids <- tables %>% html_elements("a") %>% html_attr("href") %>% str_subset("rider/")

  n <- min(nrow(results_df), length(rider_ids))
  if (n == 0) {
    return(tibble(
      event_id = character(),
      year = numeric(),
      stage_id = character(),
      category = character(),
      rank = character(),
      rider_id = character()
    ))
  }

  df <- tibble(
    event_id = as.character(event_id),
    year = as.integer(year),
    stage_id = as.character(stage_id),
    category = as.character(category),
    rank = as.character(results_df$rank[seq_len(n)]),
    rider_id = as.character(rider_ids[seq_len(n)])
  )

  return(df)
}
