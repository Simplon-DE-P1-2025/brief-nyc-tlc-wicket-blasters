-- models/final/hourly_patterns.sql
-- Patterns de demande par heure, période et type de journée

SELECT
    pickup_hour,
    pickup_weekday,
    time_period,
    is_weekend,
    is_rush_hour,

    COUNT(*)                                                    AS trip_count,
    ROUND(SUM(total_amount), 2)                                 AS total_revenue,
    ROUND(AVG(fare_amount), 2)                                  AS avg_fare,
    ROUND(AVG(tip_rate), 2)                                     AS avg_tip_rate,
    ROUND(AVG(trip_duration_minutes), 2)                        AS avg_duration_minutes,
    ROUND(AVG(trip_distance), 2)                                AS avg_distance_miles,
    ROUND(AVG(avg_speed_mph), 2)                                AS avg_speed_mph,
    ROUND(SUM(CASE WHEN is_airport_trip THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                AS pct_airport_trips,
    ROUND(SUM(CASE WHEN has_tip THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 2)                                AS pct_trips_with_tip

FROM {{ ref('clean_trips') }}
GROUP BY
    pickup_hour, pickup_weekday, time_period, is_weekend, is_rush_hour
ORDER BY
    pickup_weekday, pickup_hour
