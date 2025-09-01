# Config en functies
source("config/config.R")
source("R/scrape_stage_results.R")
source("R/scrape_stages.R")

# Parallel settings
plan(multisession, workers = 2)

# Wrapper met retry en fallback
safe_scrape <- function(event_id, year, stage_id, category) {
  out <- retry::retry(
    scrape_stage_results(event_id, year, stage_id, category),
    when = function(x) is.null(x) || inherits(x, "error"),
    max_tries = 3
  )

  if (is.null(out)) {
    return(tibble::tibble(
      event_id = character(),
      year = numeric(),
      stage_id = character(),
      category = character(),
      rank = character(),
      rider_id = character()
    ))
  }

  out
}

for (i in seq_len(nrow(EVENT_YEARS))) {
  id   <- EVENT_YEARS$event_id[i]
  year <- EVENT_YEARS$event_year[i]

  message(glue("Scraping results: {id} {year}"))

  stages <- scrape_stages(id, year)
  categories <- c("stage", "gc", "points", "kom", "youth")

  stage_cat <- tidyr::crossing(stage_id = stages$stage_id, category = categories)

  # Parallel scraping per stage/category
  furrr::future_pwalk(
    list(stage_cat$stage_id, stage_cat$category),
    function(stage_id, category) {
      df <- safe_scrape(event_id = id, year = year, stage_id = stage_id, category = category)
      stage <- stages$stage[match(stage_id, stages$stage_id)]

      if (nrow(df) > 0) {
        # sorteren consistent zoals vroeger
        df <- df %>%
          mutate(stage = stage,
                 rank_num = suppressWarnings(as.numeric(rank))) %>%
          arrange(
            stage,
            match(category, c("stage", "gc", "kom", "points", "youth")),
            rank_num,
            rider_id
          ) %>%
          select(-rank_num, -stage)

        # Bepaal pad
        file <- glue("data/raw/results/{id}/{year}/stage-{stage}-{category}.parquet")

        # Zorg dat de directory bestaat
        dir.create(dirname(file), recursive = TRUE, showWarnings = FALSE)

        # Check bestaand bestand
        if (file.exists(file)) {
          old <- tryCatch(readr::read_csv(file, show_col_types = FALSE), error = function(e) NULL)
          if (!is.null(old) && identical(old, df)) {
            message(glue("ℹ Unchanged: {file}"))
          } else {
            arrow::write_parquet(df, file)
            message(glue("✅ Updated results: {file}"))
          }
        } else {
          arrow::write_parquet(df, file)
          message(glue("🆕 Created results: {file}"))
        }

      } else {
        message(glue("ℹ No results: {id} {year} {stage_id} {category}"))
      }
    },
    .options = furrr::furrr_options(seed = TRUE)
  )
}