compute_favorites <- function(df) {

  # 1. Winsorize relevante kolommen per event
  df <- df %>%
    group_by(event_id, event_date) %>% 
    mutate(
      across(
        c(pcs_rank, event_rank, uci_points, pcs_points_season, pcs_gc_points_season, pcs_points_last_60d, pcs_gc_points, pcs_sprint_points, pcs_sprint_points_season),
        ~ psych::winsor(.x, trim = 0.01),
        .names = "{.col}_w"
      )
    ) %>% 
    ungroup()

  # 2. Combined scores
  df <- df %>%
    group_by(event_id, event_date) %>% 
    mutate(
      gc_score = -scale(pcs_rank_w)*0.5 - scale(event_rank_w)*0.5 +
                 scale(uci_points_w)*0.5 +
                 scale(pcs_gc_points_season_w)*1.5 +
                 scale(pcs_gc_points_w)*1.5,

      classic_score = -scale(pcs_rank_w)*0.5 - scale(event_rank_w)*0.5 +
                      scale(uci_points_w)*0.5 +
                      scale(pcs_points_season_w)*1.5 +
                      scale(pcs_points_last_60d_w)*1.5,

      sprinter_score = -scale(pcs_rank_w)*0.5 - scale(event_rank_w)*0.5 +
                       scale(uci_points_w)*0.5 +
                       scale(pcs_sprint_points_season_w)*1.5 +
                       scale(pcs_sprint_points_w)*1.5,

      combined_score = 0.5*gc_score + 0.3*classic_score + 0.2*sprinter_score
    ) %>% 
    ungroup()

  # 3. Top 15 berekenen
  df <- df %>%
    group_by(event_id, event_date) %>%
    arrange(desc(combined_score)) %>%
    mutate(
      rank = ifelse(row_number() <= 15, row_number(), NA_integer_)
    ) %>% 
    ungroup()

  # 4. Tier-indeling enkel voor top 15
  df_top15 <- df %>% filter(!is.na(rank))
  df_top15 <- df_top15 %>%
    mutate(
      diff_next = combined_score - lead(combined_score),
      big_gap = diff_next > sd(combined_score, na.rm = TRUE)
    ) %>%
    mutate(
      tier = case_when(
        rank == 1 ~ 1,
        big_gap & rank <= 3 ~ 2,
        TRUE ~ 3
      )
    )

  # fallback met percentielen
  if (n_distinct(df_top15$tier) < 3) {
    q <- quantile(df_top15$combined_score, probs = c(1/3, 0.8), na.rm = TRUE)
    df_top15 <- df_top15 %>%
      mutate(
        tier = case_when(
          combined_score >= q[2] ~ 1,
          combined_score >= q[1] ~ 2,
          TRUE ~ 3
        )
      )
  }

  # Teamregel: max 1 renner per ploeg in Tier 1
  df_top15 <- df_top15 %>%
    arrange(desc(combined_score)) %>%
    group_by(event_id, event_date, team_id) %>%
    mutate(
      keep_in_tier1 = ifelse(tier == 1 & row_number() == 1, TRUE, FALSE)
    ) %>%
    ungroup() %>%
    mutate(
      tier = case_when(
        tier == 1 & !keep_in_tier1 ~ 2,
        TRUE ~ tier
      )
    ) %>%
    select(-keep_in_tier1, -diff_next, -big_gap)

  # 5. Fav points
  df_top15 <- df_top15 %>%
    mutate(fav_points = plyr::mapvalues(tier, c(1,2,3), c(6,3,1)))

  # 6. Samenvoegen met rest van de renners
  df <- df %>%
    left_join(
      df_top15 %>% select(event_id, event_date, rider_id, rank, tier, fav_points),
      by = c("event_id", "event_date", "rider_id", "rank")
    )
    
    df[is.na(df)] <- 0

  return(df)
}
