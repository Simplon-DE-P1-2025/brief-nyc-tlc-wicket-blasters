-- ============================================================
-- NYC TAXI PROJECT
-- RECREATION DE LA TABLE RAW.YELLOW_TAXI_TRIPS
-- ============================================================

-- REFRESH

USE ROLE SYSADMIN;
USE WAREHOUSE NYC_TAXI_WH;
USE DATABASE NYC_TAXI_DB;
USE SCHEMA RAW;

-- ============================================================
-- SUPPRESSION DE L'ANCIENNE TABLE
-- ============================================================

DROP TABLE IF EXISTS RAW.YELLOW_TAXI_TRIPS;

-- ============================================================
-- CREATION DE LA TABLE RAW
-- Schéma officiel TLC Yellow Taxi 2024-2025
-- ============================================================

CREATE TABLE RAW.YELLOW_TAXI_TRIPS (

    -- Fournisseur du trajet
    VendorID NUMBER
        COMMENT '1=Creative Mobile Technologies, 2=Curb Mobility, 6=Myle Technologies, 7=Helix',

    -- Horodatages
    tpep_pickup_datetime TIMESTAMP_NTZ
        COMMENT 'Date et heure de prise en charge',

    tpep_dropoff_datetime TIMESTAMP_NTZ
        COMMENT 'Date et heure de dépose',

    -- Informations trajet
    passenger_count NUMBER
        COMMENT 'Nombre de passagers',

    trip_distance FLOAT
        COMMENT 'Distance du trajet en miles',

    RatecodeID NUMBER
        COMMENT 'Code tarifaire appliqué',

    store_and_fwd_flag VARCHAR(1)
        COMMENT 'Y=Store and Forward, N=Direct',

    -- Zones TLC
    PULocationID NUMBER
        COMMENT 'Pickup Location ID',

    DOLocationID NUMBER
        COMMENT 'Dropoff Location ID',

    -- Paiement
    payment_type NUMBER
        COMMENT 'Mode de paiement',

    -- Tarification
    fare_amount FLOAT
        COMMENT 'Tarif calculé par le compteur',

    extra FLOAT
        COMMENT 'Suppléments',

    mta_tax FLOAT
        COMMENT 'Taxe MTA',

    tip_amount FLOAT
        COMMENT 'Pourboire',

    tolls_amount FLOAT
        COMMENT 'Péages',

    improvement_surcharge FLOAT
        COMMENT 'Surcharge amélioration',

    total_amount FLOAT
        COMMENT 'Montant total facturé',

    congestion_surcharge FLOAT
        COMMENT 'Surcharge congestion NYC',

    airport_fee FLOAT
        COMMENT 'Frais aéroport JFK/LGA',

    cbd_congestion_fee FLOAT
        COMMENT 'Congestion Relief Zone Fee (à partir de 2025)',

    -- Métadonnées de chargement
    _loaded_at TIMESTAMP_NTZ
        DEFAULT CURRENT_TIMESTAMP(),

    _source_file VARCHAR(255)

)

COMMENT = 'Données brutes NYC Yellow Taxi 2024-2025';

-- ============================================================
-- VERIFICATION
-- ============================================================

DESC TABLE RAW.YELLOW_TAXI_TRIPS;

-- ============================================================
-- EXEMPLE DE CHARGEMENT DEPUIS LE STAGE
-- (à exécuter après vérification)
-- ============================================================

/*
COPY INTO RAW.YELLOW_TAXI_TRIPS
FROM @RAW.TLC_STAGE
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
FILE_FORMAT = (TYPE = PARQUET)
ON_ERROR = CONTINUE;
*/