-- ============================================================
-- NYC TAXI — REQUÊTES ANALYTIQUES SUR LA COUCHE FINAL
-- Base : NYC_TAXI_DB.FINAL
-- ============================================================


-- ============================================================
-- 1. DAILY_SUMMARY
-- ============================================================

-- Top 10 journées les plus actives (volume de trajets)
SELECT pickup_date, trip_count, total_revenue
FROM FINAL.DAILY_SUMMARY
ORDER BY trip_count DESC
LIMIT 10;

-- Top 10 journées les plus rentables (revenus totaux)
SELECT pickup_date, total_revenue, trip_count,
       ROUND(total_revenue / trip_count, 2) AS revenue_per_trip
FROM FINAL.DAILY_SUMMARY
ORDER BY total_revenue DESC
LIMIT 10;

-- Évolution mensuelle du volume et des revenus
SELECT pickup_year, pickup_month,
       SUM(trip_count)      AS monthly_trips,
       ROUND(SUM(total_revenue), 2) AS monthly_revenue,
       ROUND(AVG(avg_fare), 2)      AS avg_daily_fare
FROM FINAL.DAILY_SUMMARY
GROUP BY pickup_year, pickup_month
ORDER BY pickup_year, pickup_month;

-- Comparaison weekend vs semaine
SELECT is_weekend,
       SUM(trip_count)                             AS total_trips,
       ROUND(AVG(avg_fare), 2)                     AS avg_fare,
       ROUND(AVG(avg_tip_rate), 2)                 AS avg_tip_rate,
       ROUND(AVG(avg_duration_minutes), 2)         AS avg_duration,
       ROUND(AVG(avg_speed_mph), 2)                AS avg_speed
FROM FINAL.DAILY_SUMMARY
GROUP BY is_weekend;

-- Journées avec le taux de pourboire le plus élevé
SELECT pickup_date, avg_tip_rate, trip_count, avg_fare
FROM FINAL.DAILY_SUMMARY
ORDER BY avg_tip_rate DESC
LIMIT 10;

-- Évolution de la part des trajets aéroport par mois
SELECT pickup_year, pickup_month,
       ROUND(AVG(pct_airport_trips), 2) AS avg_pct_airport
FROM FINAL.DAILY_SUMMARY
GROUP BY pickup_year, pickup_month
ORDER BY pickup_year, pickup_month;


-- ============================================================
-- 2. ZONE_ANALYSIS
-- ============================================================

-- Top 20 zones de pickup (les plus actives)
SELECT zone_id, trip_count, total_revenue, avg_fare, avg_tip_rate
FROM FINAL.ZONE_ANALYSIS
WHERE zone_role = 'pickup'
ORDER BY trip_count DESC
LIMIT 20;

-- Top 20 zones de dropoff (les plus actives)
SELECT zone_id, trip_count, total_revenue, avg_fare
FROM FINAL.ZONE_ANALYSIS
WHERE zone_role = 'dropoff'
ORDER BY trip_count DESC
LIMIT 20;

-- Zones de pickup avec le revenu moyen par trajet le plus élevé (min. 1000 trajets)
SELECT zone_id, avg_fare, avg_tip_rate, trip_count
FROM FINAL.ZONE_ANALYSIS
WHERE zone_role = 'pickup'
  AND trip_count >= 1000
ORDER BY avg_fare DESC
LIMIT 20;

-- Zones les plus généreuses en pourboire (pickup, min. 500 trajets)
SELECT zone_id, avg_tip_rate, pct_trips_with_tip, avg_fare, trip_count
FROM FINAL.ZONE_ANALYSIS
WHERE zone_role = 'pickup'
  AND trip_count >= 500
ORDER BY avg_tip_rate DESC
LIMIT 15;

-- Zones aéroport : volume et revenus
SELECT zone_id, zone_role, trip_count, pct_airport_trips,
       avg_fare, avg_distance_miles
FROM FINAL.ZONE_ANALYSIS
WHERE pct_airport_trips > 50
ORDER BY trip_count DESC;

-- Zones avec les trajets les plus longs en distance
SELECT zone_id, zone_role, avg_distance_miles, avg_duration_minutes, avg_fare
FROM FINAL.ZONE_ANALYSIS
WHERE zone_role = 'pickup'
  AND trip_count >= 500
ORDER BY avg_distance_miles DESC
LIMIT 15;

-- Déséquilibre pickup vs dropoff par zone (zones avec surplus d'arrivées)
SELECT p.zone_id,
       p.trip_count AS pickup_count,
       d.trip_count AS dropoff_count,
       d.trip_count - p.trip_count AS dropoff_surplus
FROM FINAL.ZONE_ANALYSIS p
JOIN FINAL.ZONE_ANALYSIS d
    ON p.zone_id = d.zone_id
   AND d.zone_role = 'dropoff'
WHERE p.zone_role = 'pickup'
ORDER BY ABS(d.trip_count - p.trip_count) DESC
LIMIT 20;


-- ============================================================
-- 3. HOURLY_PATTERNS
-- ============================================================

-- Heatmap : volume moyen par heure et jour de semaine
SELECT pickup_weekday, pickup_hour,
       SUM(trip_count) AS total_trips
FROM FINAL.HOURLY_PATTERNS
GROUP BY pickup_weekday, pickup_hour
ORDER BY pickup_weekday, pickup_hour;

-- Heures de pointe vs heures creuses (toute semaine confondue)
SELECT pickup_hour,
       SUM(trip_count)              AS total_trips,
       ROUND(AVG(avg_fare), 2)      AS avg_fare,
       ROUND(AVG(avg_speed_mph), 2) AS avg_speed,
       ROUND(AVG(avg_tip_rate), 2)  AS avg_tip_rate
FROM FINAL.HOURLY_PATTERNS
GROUP BY pickup_hour
ORDER BY pickup_hour;

-- Rush hour vs hors pointe : comparaison des métriques
SELECT is_rush_hour,
       SUM(trip_count)                      AS total_trips,
       ROUND(AVG(avg_fare), 2)              AS avg_fare,
       ROUND(AVG(avg_duration_minutes), 2)  AS avg_duration,
       ROUND(AVG(avg_speed_mph), 2)         AS avg_speed,
       ROUND(AVG(avg_tip_rate), 2)          AS avg_tip_rate
FROM FINAL.HOURLY_PATTERNS
GROUP BY is_rush_hour;

-- Période de la journée la plus active
SELECT time_period,
       SUM(trip_count)              AS total_trips,
       ROUND(AVG(avg_fare), 2)      AS avg_fare,
       ROUND(AVG(avg_tip_rate), 2)  AS avg_tip_rate,
       ROUND(AVG(avg_speed_mph), 2) AS avg_speed
FROM FINAL.HOURLY_PATTERNS
GROUP BY time_period
ORDER BY total_trips DESC;

-- Meilleur moment de la semaine pour les pourboires
SELECT pickup_weekday, pickup_hour,
       ROUND(AVG(avg_tip_rate), 2)  AS avg_tip_rate,
       SUM(trip_count)              AS trip_count
FROM FINAL.HOURLY_PATTERNS
GROUP BY pickup_weekday, pickup_hour
ORDER BY avg_tip_rate DESC
LIMIT 15;

-- Nuit vs matin : comparaison vitesse et durée
SELECT
    CASE WHEN pickup_hour BETWEEN 0 AND 5 THEN 'Nuit (0h-5h)'
         WHEN pickup_hour BETWEEN 6 AND 11 THEN 'Matin (6h-11h)'
         WHEN pickup_hour BETWEEN 12 AND 17 THEN 'Après-midi (12h-17h)'
         ELSE 'Soir (18h-23h)'
    END AS plage_horaire,
    SUM(trip_count)                     AS total_trips,
    ROUND(AVG(avg_speed_mph), 2)        AS avg_speed,
    ROUND(AVG(avg_duration_minutes), 2) AS avg_duration
FROM FINAL.HOURLY_PATTERNS
GROUP BY plage_horaire
ORDER BY total_trips DESC;


-- ============================================================
-- 4. VENDOR_PERFORMANCE
-- ============================================================

-- Classement global des fournisseurs
SELECT vendor_name, trip_count, market_share_pct,
       total_revenue, avg_fare, avg_tip_rate
FROM FINAL.VENDOR_PERFORMANCE
ORDER BY market_share_pct DESC;

-- Qualité de service : vitesse et durée par fournisseur
SELECT vendor_name, avg_speed_mph, avg_duration_minutes,
       avg_distance_miles, trip_count
FROM FINAL.VENDOR_PERFORMANCE
ORDER BY avg_speed_mph DESC;

-- Fournisseur le plus généreux en pourboires
SELECT vendor_name, avg_tip_rate, pct_trips_with_tip, avg_fare
FROM FINAL.VENDOR_PERFORMANCE
ORDER BY avg_tip_rate DESC;

-- Taux de store-and-forward par fournisseur (trajets en mode hors-ligne)
SELECT vendor_name, pct_store_and_fwd, trip_count
FROM FINAL.VENDOR_PERFORMANCE
ORDER BY pct_store_and_fwd DESC;

-- Part des trajets aéroport par fournisseur
SELECT vendor_name, pct_airport_trips, trip_count, avg_fare
FROM FINAL.VENDOR_PERFORMANCE
ORDER BY pct_airport_trips DESC;

-- Revenu total par fournisseur
SELECT vendor_name,
       total_revenue,
       ROUND(total_revenue / trip_count, 2) AS revenue_per_trip,
       market_share_pct
FROM FINAL.VENDOR_PERFORMANCE
ORDER BY total_revenue DESC;


-- ============================================================
-- 5. PAYMENT_ANALYSIS
-- ============================================================

-- Distribution globale des modes de paiement (toutes périodes)
SELECT payment_type_label,
       SUM(trip_count)                                 AS total_trips,
       ROUND(SUM(trip_count) * 100.0
             / SUM(SUM(trip_count)) OVER (), 2)        AS pct_total,
       ROUND(AVG(avg_fare), 2)                         AS avg_fare,
       ROUND(AVG(avg_tip_rate), 2)                     AS avg_tip_rate,
       ROUND(AVG(pct_trips_with_tip), 2)               AS avg_pct_with_tip
FROM FINAL.PAYMENT_ANALYSIS
GROUP BY payment_type_label
ORDER BY total_trips DESC;

-- Évolution mensuelle Credit Card vs Cash
SELECT pickup_year, pickup_month, payment_type_label,
       trip_count, pct_of_monthly_trips, avg_tip_rate
FROM FINAL.PAYMENT_ANALYSIS
WHERE payment_type_label IN ('Credit Card', 'Cash')
ORDER BY pickup_year, pickup_month, payment_type_label;

-- Tip rate moyen par mode de paiement
SELECT payment_type_label,
       ROUND(AVG(avg_tip_rate), 2)         AS avg_tip_rate,
       ROUND(AVG(avg_tip_amount), 2)       AS avg_tip_amount,
       ROUND(AVG(pct_trips_with_tip), 2)   AS pct_with_tip
FROM FINAL.PAYMENT_ANALYSIS
GROUP BY payment_type_label
ORDER BY avg_tip_rate DESC;

-- Évolution de la part Flex Fare (mode récent) dans le temps
SELECT pickup_year, pickup_month,
       pct_of_monthly_trips AS pct_flex_fare,
       trip_count
FROM FINAL.PAYMENT_ANALYSIS
WHERE payment_type_label = 'Flex Fare'
ORDER BY pickup_year, pickup_month;

-- Mois avec le plus fort taux de pourboire (Credit Card uniquement)
SELECT pickup_year, pickup_month, avg_tip_rate, trip_count
FROM FINAL.PAYMENT_ANALYSIS
WHERE payment_type_label = 'Credit Card'
ORDER BY avg_tip_rate DESC
LIMIT 10;


-- ============================================================
-- 6. MONTHLY_KPI
-- ============================================================

-- Vue d'ensemble mensuelle 2024-2025
SELECT pickup_year, pickup_month,
       trip_count, total_revenue,
       avg_fare, avg_tip_rate,
       avg_duration_minutes, avg_distance_miles
FROM FINAL.MONTHLY_KPI
ORDER BY pickup_year, pickup_month;

-- Impact de la CBD congestion fee (active depuis janvier 2025)
SELECT pickup_year, pickup_month,
       avg_cbd_congestion_fee,
       total_cbd_congestion_fee,
       trips_with_cbd_fee,
       trip_count,
       ROUND(trips_with_cbd_fee * 100.0 / trip_count, 2) AS pct_trips_with_cbd
FROM FINAL.MONTHLY_KPI
ORDER BY pickup_year, pickup_month;

-- Comparaison 2024 vs 2025 (mois identiques)
SELECT a.pickup_month,
       a.trip_count                                             AS trips_2024,
       b.trip_count                                             AS trips_2025,
       ROUND((b.trip_count - a.trip_count) * 100.0
             / a.trip_count, 2)                                AS pct_growth,
       ROUND(a.avg_fare, 2)                                    AS avg_fare_2024,
       ROUND(b.avg_fare, 2)                                    AS avg_fare_2025
FROM FINAL.MONTHLY_KPI a
JOIN FINAL.MONTHLY_KPI b
    ON a.pickup_month = b.pickup_month
   AND b.pickup_year  = 2025
WHERE a.pickup_year = 2024
ORDER BY a.pickup_month;

-- Évolution du base_fare_ratio : part du tarif de base dans le total
SELECT pickup_year, pickup_month,
       avg_base_fare_ratio,
       avg_total_surcharges,
       avg_fare
FROM FINAL.MONTHLY_KPI
ORDER BY pickup_year, pickup_month;

-- Mois avec le plus fort volume de trajets aéroport
SELECT pickup_year, pickup_month,
       pct_airport_trips, trip_count
FROM FINAL.MONTHLY_KPI
ORDER BY pct_airport_trips DESC
LIMIT 10;

-- Évolution des trajets en heure de pointe vs weekend
SELECT pickup_year, pickup_month,
       pct_rush_hour_trips,
       pct_weekend_trips,
       pct_trips_with_tip
FROM FINAL.MONTHLY_KPI
ORDER BY pickup_year, pickup_month;


-- ============================================================
-- REQUÊTES CROISÉES (plusieurs tables FINAL)
-- ============================================================

-- Corrélation zone active + heure de pointe
-- (zones avec le plus de trajets rush hour)
SELECT z.zone_id,
       z.trip_count                              AS total_zone_trips,
       h.trip_count                              AS rush_hour_trips,
       ROUND(h.avg_fare, 2)                      AS rush_avg_fare
FROM FINAL.ZONE_ANALYSIS z
JOIN FINAL.HOURLY_PATTERNS h
    ON h.is_rush_hour = TRUE
WHERE z.zone_role = 'pickup'
  AND z.trip_count >= 5000
ORDER BY z.trip_count DESC
LIMIT 10;

-- Journées avec revenus élevés ET fort tip rate
SELECT pickup_date, trip_count, total_revenue,
       avg_tip_rate, avg_fare, pct_trips_with_tip
FROM FINAL.DAILY_SUMMARY
WHERE avg_tip_rate > 15
  AND trip_count > 50000
ORDER BY total_revenue DESC
LIMIT 10;
