# utils.R

# Schoonmaken van namen
clean_name <- function(name) {
  name %>%
    str_squish() %>%
    str_replace_all("[^[:alnum:] ]", "")
}

# Omzetten naar numeriek veilig
safe_numeric <- function(x) {
  suppressWarnings(as.numeric(x))
}