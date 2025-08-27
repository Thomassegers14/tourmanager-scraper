library(dplyr)
library(tidyr)
library(glue)
library(readr)

# ---- Parameters ----
source("config/config.R")

for (i in seq_len(nrow(EVENT_YEARS))) {
  id <- EVENT_YEARS$event_id[i]
  year <- EVENT_YEARS$event_year[i]

  # ---- Data inladen ----
  stages <- read.csv(glue("data/processed/stages/stages_{id}_{year}.csv"))
  results <- read.csv(glue("data/processed/results/{id}_{year}_all_stage_results.csv"))
  startlist <- read.csv(glue("data/processed/startlists_favorites/startlist_{id}_{year}.csv"))

  # ---- Stage results ----
  stage_results <- results %>%
    filter(category == "stage") %>%
    mutate(rank = as.integer(rank)) %>%
    filter(rank <= 10) %>%
    # Voeg een kolom toe die aangeeft of het een TTT is
    left_join(
      stages %>% select(stage_id, stage_name),
      by = "stage_id"
    ) %>%
    mutate(
      is_ttt = grepl("\\(TTT\\)", stage_name)
    ) %>%
    # kies het juiste puntenschema
    rowwise() %>%
    mutate(
      points = ifelse(is_ttt,
                      stage_points_ttt$points[match(rank, stage_points_ttt$rank)],
                      stage_points$points[match(rank, stage_points$rank)])
    ) %>%
    ungroup() %>%
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

  # ---- Alles samen ----
  all_points <- bind_rows(
    stage_results,
    daily_class_results,
    final_class_results
  ) %>%
    group_by(stage_id, rider_id) %>%
    summarise(stage_points = sum(points, na.rm = TRUE), .groups = "drop")

  # ---- Stage info ----
  stage_info <- stages %>%
    select(stage_id, stage = stage) %>%
    mutate(stage = as.integer(stage))

  final_stage_number <- max(stage_info$stage, na.rm = TRUE) + 1
  if ("final" %in% all_points$stage_id) {
    stage_info <- bind_rows(
      stage_info,
      tibble(stage_id = "final", stage = final_stage_number)
    )
  }

  # ---- Koppel renners (voor namen) ----
  all_points_named <- all_points %>%
    left_join(startlist %>% select(rider_id, rider_name), by = "rider_id") %>%
    left_join(stage_info, by = "stage_id")

  # ---- Cross join alle renners × beschikbare stages ----
  available_stage_ids <- unique(all_points_named$stage_id)

  all_combinations <- tidyr::crossing(
    stage_id = available_stage_ids,
    rider_id = unique(startlist$rider_id)
  ) %>%
    left_join(startlist %>% select(rider_id, rider_name), by = "rider_id") %>%
    left_join(stage_info, by = "stage_id")

  # ---- Join met berekende punten ----
  rider_stage_summary <- all_combinations %>%
    left_join(all_points_named %>% select(stage_id, rider_id, stage_points),
      by = c("stage_id", "rider_id")
    ) %>%
    mutate(stage_points = replace_na(stage_points, 0)) %>%
    arrange(rider_id, stage) %>%
    group_by(rider_id) %>%
    mutate(cumulative_points = cumsum(stage_points)) %>%
    ungroup() %>%
    select(rider_id, rider_name, stage_id, stage, stage_points, cumulative_points)

  # ---- Wegschrijven ----
  out_path <- glue("data/processed/points/rider_stage_summary_{id}_{year}.csv")
  write_csv(rider_stage_summary, out_path)

  message(glue("✅ Rider summary weggeschreven naar {out_path}"))
}
