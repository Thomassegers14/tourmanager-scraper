source("config/config.R")

for (i in seq_len(nrow(EVENT_YEARS))) {
  id   <- EVENT_YEARS$event_id[i]
  year <- EVENT_YEARS$event_year[i]

  # Verzamel parquet-bestanden
  files <- list.files(
    glue("data/raw/results/{id}/{year}"),
    full.names = TRUE,
    pattern = "\\.parquet$",
    recursive = TRUE
  )

  if (length(files) == 0) {
    message(glue("ℹ No parquet files found for {id} {year}"))
    next
  }

  ds <- open_dataset(files, format = "parquet")

  stages <- scrape_stages(id, year) %>%
    select(stage_id, stage)

  # Alles wat Arrow aankan, laten we in Arrow gebeuren
  all_results <- ds %>%
    left_join(stages, by = "stage_id") %>%
    collect() %>%   # nu terug naar R voor factor/as.numeric
    mutate(
      category = factor(category, levels = c("stage", "gc", "kom", "points", "youth")),
      rank_num = suppressWarnings(as.numeric(rank))
    ) %>%
    arrange(stage, category, rank_num, rider_id) %>%
    select(-c(rank_num, stage))

  if (nrow(all_results) > 0) {
    dir.create("data/processed/results", showWarnings = FALSE, recursive = TRUE)
    file <- glue("data/processed/results/{id}_{year}_all_stage_results.csv")
    fwrite(all_results, file)
    message(glue("✅ Saved results: {file}"))
  } else {
    message(glue("ℹ No results available yet for {id} {year}"))
  }
}
