scrape_stages <- function(id, year) {
  # Laad pagina
  page <- read_html(glue::glue("https://www.procyclingstats.com/race/{id}/{year}/route/stages"))

  # ---- Alle tabellen pakken ----
  tables <- page %>% html_elements("table")

  # Eerste tabel = stages
  stages_df <- tables[[1]] %>%
    html_table(fill = TRUE, header = TRUE)

  # Lege kolom verwijderen
  stages_df <- stages_df[, colnames(stages_df) != ""]

  stages <- as_tibble(stages_df)

  # Stage_id toevoegen uit href
  stage_ids <- tables[[1]] %>%
    html_elements("tbody tr td:nth-child(3) a") %>%
    html_attr("href")

  # Stage types mapping
  stageTypes <- data.frame(
    stageType = c(" Flat", "Hills, flat finish", "Hills, uphill finish", "Mountains, flat finish", "Mountains, uphill finish"),
    stageTypeCode = c("p1", "p2", "p3", "p4", "p5")
  )

  # Haal de type codes van de etappes op
  stageTypeCodes <- tables[[1]] %>%
    html_elements(".profile") %>%
    html_attr("class") %>%
    discard(~ str_detect(.x, " p ")) %>%
    str_remove_all("icon profile | mg_rp4") %>%
    str_trim()

  stages <- stages %>%
    filter(Date != "") %>% # somrij eruit
    mutate(
      stage_id = stage_ids,
      stage_nr = str_extract(`#`, "\\d+"),
    date        = as.Date(glue::glue("{Date}/{year}"), format = "%d/%m/%Y"),
      departure = Departure,
      arrival = Arrival,
      stage_type = plyr::mapvalues(stageTypeCodes, stageTypes$stageTypeCode, stageTypes$stageType, warn_missing = FALSE),
      distance_km = as.numeric(str_replace(Distance, ",", ".")),
      vertical_m = as.numeric(str_replace(`Vertical meters`, ",", "."))
    ) %>%
    select(stage_id, date, stage_nr, stage_type, departure, arrival, distance_km, vertical_m)

  # Tweede tabel = hardest stages
  hardest_df <- tables[[2]] %>%
    html_table(fill = TRUE) %>%
    `colnames<-`(c("stage_rank", "stage_name", "profile_score"))

  hardest_ids <- tables[[2]] %>%
    html_elements("tbody tr td:nth-child(2) a") %>%
    html_attr("href")

  hardest <- hardest_df %>%
    mutate(
      stage_id = hardest_ids,
      profile_score = as.numeric(str_extract(.[[3]], "\\d+"))
    ) %>%
    select(stage_id, profile_score)

  # ---- Joinen ----
  result <- stages %>%
    left_join(hardest, by = "stage_id") %>%
    arrange(as.numeric(stage_nr))

  return(result)
}
