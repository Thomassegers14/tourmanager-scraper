source("R/get_selections.R")

selections <- get_selections() %>% process_selections()
eventId <- "vuelta-a-espana"
eventYear <- 2025

dir.create("data/processed/selections", showWarnings = FALSE, recursive = TRUE)
file <- glue("data/processed/selections/selections_{eventId}_{eventYear}.csv")
write_csv(selections, file)
