# compute_favorites_run.R
library(dplyr)
library(purrr)

# Functie inladen
source("R/compute_favorites.R")

# --- 1. Inlezen van startlists ---
startlists <- purrr::map_df(
  list.files("data/processed/startlists", full.names = TRUE),
  ~ read.csv(.x, encoding = "UTF-8")
) %>%
  mutate(
    across(c(pcs_rank, event_rank), as.numeric)
  )

# --- 2. Bereken favorieten ---
startlists_enriched <- compute_favorites(startlists)

# --- 3. Wegschrijven per event ---
output_dir <- "data/processed/startlists_favorites/"
if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)

startlists_enriched %>%
  group_by(event_id, event_date) %>%
  group_split() %>%    # split in een lijst van dataframes per event
  walk(function(df) {
    file_name <- paste0(output_dir,
                        "startlist_",
                        unique(df$event_id), "_",
                        unique(lubridate::year(df$event_date)), ".csv")
    write.csv(df, file_name, row.names = FALSE)
  })

cat("✅ Startlists verrijkt en weggeschreven per event naar ", output_dir, "\n")
