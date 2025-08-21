message("=== START MASTER SCRAPER ===")

# Run startlists
message("--- Running startlist scraper ---")
source("scripts/run_scrape_startlists.R")

# Run stages
message("--- Running stages scraper ---")
source("scripts/run_scrape_stages.R")

# Run results
message("--- Running results scraper ---")
source("scripts/run_scrape_results.R")

message("=== MASTER SCRAPER FINISHED ===")
