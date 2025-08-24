library(dplyr)
library(tidyr)
library(tibble)

# 🟡 Stage points
stage_points <- tibble(
  rank = 1:10,
  points = c(30, 25, 20, 14, 12, 10, 8, 6, 4, 2)
)

# 🟡 Stage type weights
stage_weight <- tibble(
  type = c("Flat", "Hilly", "Mountain", "TT"),
  factor = c(1.0, 1.1, 1.3, 1.2)
)

# 🟡 Daily classification points
daily_class_points <- tribble(
  ~category, ~rank, ~points,
  "gc", 1, 5,
  "gc", 2, 3,
  "gc", 3, 2,
  "kom", 1, 3,
  "kom", 2, 2,
  "kom", 3, 1,
  "points", 1, 3,
  "points", 2, 2,
  "points", 3, 1,
  "youth", 1, 3,
  "youth", 2, 2,
  "youth", 3, 1
)

# 🟡 Final classification points
final_class_points <- bind_rows(
  tibble(
    category = "gc",
    rank = 1:20,
    points = c(90, 80, 75, 70, 65, 60, 55, 50, 45, 40,
               38, 36, 34, 32, 30, 28, 26, 24, 22, 20)
  ),
  tibble(
    category = "kom",
    rank = 1:5,
    points = c(40, 30, 20, 15, 10)
  ),
  tibble(
    category = "points",
    rank = 1:5,
    points = c(40, 30, 20, 15, 10)
  ),
  tibble(
    category = "youth",
    rank = 1:5,
    points = c(40, 30, 20, 15, 10)
  )
)
