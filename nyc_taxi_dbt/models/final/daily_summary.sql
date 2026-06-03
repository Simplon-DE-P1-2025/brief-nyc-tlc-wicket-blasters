-- models/final/daily_summary.sql
-- Agrégations journalières : volume, revenus, qualité de service

SELECT
    pickup_date,
    pickup_year,
    pickup_month,
    pickup_weekday,
    is_weekend,

    COUNT(*)                                                    AS trip_count,
    SUM(total_amount)                                           AS total_revenue,
    ROUND(AVG(fare_amount), 2)                                  AS avg_fare,
    ROUND(AVG(total_amount), 2)                                 AS avg_total_amount,
    ROUND(AVG(tip_rate), 2)                                     AS avg_tip_rate,
    ROUND(AVG(trip_duration_minutes), 2)                        AS avg_duration_minutes,
    ROUND(AVG(trip_distance), 2)                                AS avg_distance_miles,
    ROUND(AVG(avg_speed_mph), 2)                                AS avg_speed_mph,
    ROUND(AVG(passenger_count), 2)                              AS avg_passenger_count,
    ROUND(AVG(total_surcharges), 2)                             AS avg_total_surcharges,
    ROUND(AVG(base_fare_ratio), 2)                              AS avg_base_fare_ratio,
    ROUND(SUM(CASE WHEN is_airport_trip THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                AS pct_airport_trips,
    ROUND(SUM(CASE WHEN has_tip THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                AS pct_trips_with_tip,
    ROUND(SUM(CASE WHEN is_rush_hour THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                AS pct_rush_hour_trips

FROM {{ ref('clean_trips') }}
GROUP BY
    pickup_date, pickup_year, pickup_month, pickup_weekday, is_weekend
ORDER BY
    pickup_date
