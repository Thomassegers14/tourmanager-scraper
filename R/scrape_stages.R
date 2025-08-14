scrape_stages <- function(id, year) {
  # Laad pagina
  page <- read_html(glue::glue("https://www.procyclingstats.com/race/{id}/{year}"))
  
  # Zoek de tabel waar "Stage" in een <th> staat
  stage_table_node <- page %>%
    html_elements(".basic") %>%
    keep(~ any(str_detect(html_text(html_elements(.x, "th")), regex("stage", ignore_case = TRUE))))
  
  # Zet de juiste tabel om naar dataframe
  stagesTables <- stage_table_node %>% html_table()
  
  # Haal stage links op
  stageIds <- stage_table_node %>% 
    html_elements("a") %>% 
    html_attr("href") %>% 
    keep(~ str_detect(.x, "stage"))
  
  # Stage types mapping
  stageTypes <- data.frame(
    stageType = c(" Flat","Hills, flat finish","Hills, uphill finish","Mountains, flat finish","Mountains, uphill finish"),
    stageTypeCode = c("p1","p2","p3","p4","p5")
  )
  
  # Haal de type codes van de etappes op
  stageTypeCodes <- stage_table_node %>% 
    html_elements(".profile") %>% 
    html_attr("class") %>% 
    discard(~ str_detect(.x, " p ")) %>% 
    str_remove_all("icon profile | mg_rp4") %>% 
    str_trim()
  
  # Bouw dataframe
  stages <- stagesTables[[1]] %>%
    select(-3) %>% 
    filter(!str_detect(Stage, "Restday")) %>% 
    filter(row_number() <= n() - 1) %>% 
    mutate(
      stage_id = stageIds,
      stage = row_number(),
      stage_type = plyr::mapvalues(stageTypeCodes, stageTypes$stageTypeCode, stageTypes$stageType, warn_missing = FALSE)
    ) %>% 
    select(stage, stage_id, stage_name = Stage, stage_type)
  
  return(stages)
}