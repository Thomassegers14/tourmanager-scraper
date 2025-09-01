message("=== START RESULTS PROCESSING ===")

# Run startlists
message("--- Running results scraper ---")
source("scripts/run_scrape_results.R")

# Run startlists
message("--- Running process results ---")
source("scripts/process_stage_results.R")

# Run stages
message("--- Compute participant ranking ---")
source("scripts/compute_scores.R")

# Run results
message("--- Compute rider points ---")
source("scripts/compute_rider_points.R")

message("=== RESULTS PROCESSING FINISHED ===")
