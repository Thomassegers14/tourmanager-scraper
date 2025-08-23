readRenviron(".Renviron")

# Laden
library(DBI)
library(RPostgres)

# Functie om inzendingen op te halen
get_selections <- function() {
  con <- NULL
  selections <- NULL
  
  tryCatch({
    # Verbinden met de database
    con <- dbConnect(
        Postgres(),
        dbname   = Sys.getenv("DB_NAME"),
        host     = Sys.getenv("DB_HOST"),
        port     = as.integer(Sys.getenv("DB_PORT")),
        user     = Sys.getenv("DB_USER"),
        password = Sys.getenv("DB_PASS"),
        sslmode  = "require"
    )

    # Data ophalen
    selections <- dbGetQuery(con, "SELECT * FROM inzendingen")
    
  }, error = function(e) {
    message("Er is een fout opgetreden bij het ophalen van de inzendingen: ", e$message)
  }, finally = {
    # Connectie netjes sluiten
    if (!is.null(con)) dbDisconnect(con)
  })
  
  return(selections)
}

process_selections <- function(df) {
    df <- df %>% 
    mutate(
        rider_ids = str_remove_all(rider_ids, "[\\{\\}\"]"),
        rider_names = str_remove_all(rider_names, "[\\{\\}\"]")
    ) %>%
    mutate(
        rider_ids = str_split(rider_ids, ","),
        rider_names = str_split(rider_names, ",")
    ) %>%
    unnest(c(rider_ids, rider_names)) %>%
    rename(
        rider_id = rider_ids,
        rider_name = rider_names
    ) %>% 
    mutate(across(everything(), str_trim)) %>%
    select(id, tijdstip, voornaam, achternaam, email, rider_id, rider_name)

    df <- df %>%
      group_by(voornaam, achternaam, email) %>%
      filter(tijdstip == max(tijdstip)) %>%
      ungroup()

    return(df)

}