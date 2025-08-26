library(dplyr)
library(tidyr)
library(glue)
library(readr)

# functies laden
source("R/point_system.R")

# ---- Parameters ----
source("config/config.R")

for (i in seq_len(nrow(EVENT_YEARS))) {
  id <- EVENT_YEARS$event_id[i]
  year <- EVENT_YEARS$event_year[i]


  # ---- Data inladen ----
  startlist <- read_csv(glue("data/processed/startlists_favorites/startlist_{id}_{year}.csv"))
  stages <- read_csv(glue("data/processed/stages/stages_{id}_{year}.csv"))
  results <- read_csv(glue("data/processed/results/{id}_{year}_all_stage_results.csv"))
  selections <- read_csv(glue("data/processed/selections/selections_{id}_{year}.csv"))

  # ---- Stage results ----
  stage_results <- results %>%
    filter(category == "stage") %>%
    mutate(rank = as.integer(rank)) %>%
    filter(rank <= 10) %>%
    left_join(stage_points, by = "rank") %>%
    select(stage_id, rider_id, points)

  # ---- Daily class results ----
  daily_class_results <- results %>%
    filter(!grepl("stage-21", stage_id) & category %in% c("gc", "kom", "points", "youth")) %>%
    mutate(rank = as.integer(rank)) %>%
    filter(rank <= 3) %>%
    left_join(daily_class_points, by = c("category", "rank")) %>%
    select(stage_id, rider_id, points)

  # ---- Final class results ----
  final_class_results <- results %>%
    filter(grepl("stage-21", stage_id) & category %in% c("gc", "kom", "points", "youth")) %>%
    mutate(rank = as.integer(rank)) %>%
    filter((category == "gc" & rank <= 20) | rank <= 5) %>%
    left_join(final_class_points, by = c("category", "rank")) %>%
    mutate(stage_id = "final") %>%
    select(stage_id, rider_id, points)

  # ---- Rider total scores ----
  rider_scores <- bind_rows(
    stage_results,
    daily_class_results,
    final_class_results
  ) %>%
    group_by(rider_id) %>%
    summarise(total_points = sum(points, na.rm = TRUE), .groups = "drop")

  # ---- Stage info ----
  stage_info <- stages %>%
    select(stage_id, stage = stage) %>%
    mutate(stage = as.integer(stage))

  # ---- Alle punten op etappes ----
  stage_all_points <- bind_rows(
    stage_results,
    daily_class_results
  ) %>%
    left_join(stage_info, by = "stage_id")

  stage_scores_long <- stage_all_points %>%
    left_join(selections, by = "rider_id") %>%
    filter(!is.na(id)) # alleen gekozen renners

  participant_stage_points <- stage_scores_long %>%
    group_by(stage, stage_id, id, voornaam, achternaam) %>%
    summarise(stage_points = sum(points, na.rm = TRUE), .groups = "drop")

  final_stage_number <- max(stage_info$stage, na.rm = TRUE) + 1
  final_scores_long <- final_class_results %>%
    left_join(selections, by = "rider_id") %>%
    filter(!is.na(id)) %>%
    mutate(stage_id = "final", stage = final_stage_number) %>%
    group_by(stage, stage_id, id, voornaam, achternaam) %>%
    summarise(stage_points = sum(points, na.rm = TRUE), .groups = "drop")

  all_participant_stage_scores <- bind_rows(participant_stage_points, final_scores_long)

  # ---- Welke stages hebben effectief resultaten? ----
  available_stage_ids <- unique(all_participant_stage_scores$stage_id)

  # Lookup tabel voor stage nummer
  stage_lookup <- stage_info %>%
    filter(stage_id %in% available_stage_ids)

  if ("final" %in% unique(all_participant_stage_scores$stage_id)) {
    stage_lookup <- bind_rows(
      stage_lookup,
      tibble(stage_id = "final", stage = final_stage_number)
    )
  }

  # ---- Cross join deelnemers × beschikbare stages ----
  all_combinations <- tidyr::crossing(
    stage_id = available_stage_ids,
    id = selections$id
  ) %>%
    left_join(stage_lookup, by = "stage_id") %>%
    left_join(selections %>% distinct(id, voornaam, achternaam), by = "id")

  # ---- Join met berekende punten ----
  participant_stage_ranked <- all_combinations %>%
    left_join(
      all_participant_stage_scores %>%
        select(stage_id, id, stage_points),
      by = c("stage_id", "id")
    ) %>%
    mutate(stage_points = replace_na(stage_points, 0)) %>%
    arrange(id, stage) %>%
    group_by(id) %>%
    mutate(cumulative_points = cumsum(stage_points)) %>%
    ungroup() %>%
    group_by(stage) %>%
    arrange(desc(cumulative_points)) %>%
    mutate(rank = row_number()) %>%
    ungroup()

  # ---- Wegschrijven ----
  out_path <- glue("data/processed/ranking/ranking_by_stage_{id}_{year}.csv")
  write_csv(participant_stage_ranked, out_path)

  message(glue("✅ Scores weggeschreven naar {out_path}"))
}
