# NYC Yellow Taxi — Pipeline de données 2024-2025

Pipeline de données complet sur les trajets des taxis jaunes de New York City, de l'ingestion des fichiers bruts jusqu'à un dashboard analytique interactif.

---

## Architecture

```
NYC TLC (Parquet)
       │
       ▼
┌─────────────────────────────────────────────────────┐
│               Snowflake — NYC_TAXI_DB               │
│                                                     │
│  RAW.YELLOW_TAXI_TRIPS                              │
│       │  (données brutes TLC, ~40M trajets)         │
│       │                                             │
│       ▼  dbt (staging)                              │
│  STAGING.CLEAN_TRIPS                                │
│       │  (nettoyage, enrichissement, labels)        │
│       │                                             │
│       ▼  dbt (final)                                │
│  FINAL.DAILY_SUMMARY                                │
│  FINAL.ZONE_ANALYSIS                                │
│  FINAL.HOURLY_PATTERNS                              │
│  FINAL.VENDOR_PERFORMANCE                           │
│  FINAL.PAYMENT_ANALYSIS                             │
│  FINAL.MONTHLY_KPI                                  │
└─────────────────────────────────────────────────────┘
       │
       ▼
  Streamlit Dashboard
```

---

## Structure du projet

```
.
├── .github/workflows/
│   ├── dbt_ci.yml          # Tests sur PR (staging uniquement)
│   ├── dbt_cd.yml          # Déploiement sur merge master
│   └── dbt_ingestion.yml   # Pipeline complet (mensuel + manuel)
├── Docs/
│   ├── data_dictionary_trip_records_yellow.pdf
│   ├── Guide – Projet NYC Taxi.docx
│   └── Ressources_et_Monitoring_NYC_Taxi.docx
├── exploration/
│   └── nyc_taxi_exploration.ipynb
├── nyc_taxi_dbt/
│   ├── macros/generate_schema_name.sql
│   ├── models/
│   │   ├── staging/clean_trips.sql
│   │   └── final/
│   │       ├── daily_summary.sql
│   │       ├── zone_analysis.sql
│   │       ├── hourly_patterns.sql
│   │       ├── vendor_performance.sql
│   │       ├── payment_analysis.sql
│   │       └── monthly_kpi.sql
│   ├── seeds/taxi_zones.csv
│   ├── analyses/queries_final.sql
│   ├── dbt_project.yml
│   └── profiles.yml
├── monitoring/
│   └── pipeline_monitor.py
├── python/
│   └── load_datasets_to_snowflake.py
├── dashboard.py
├── requirements.txt
└── .env.example
```

---

## Prérequis

- Python 3.11+
- Compte Snowflake avec un rôle `SYSADMIN`
- dbt-fusion ou dbt-snowflake 1.11.5+

---

## Installation

```bash
# 1. Cloner le repo
git clone <repo-url>
cd Brief-11-nyc-tlc-wicket-blasters

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Configurer les variables d'environnement
cp .env.example .env
# Remplir .env avec vos credentials Snowflake
```

Contenu du fichier `.env` :

```env
SNOWFLAKE_ACCOUNT=<account-id>
SNOWFLAKE_USER=<username>
SNOWFLAKE_PASSWORD=<password>
SNOWFLAKE_WAREHOUSE=NYC_TAXI_WH
SNOWFLAKE_DATABASE=NYC_TAXI_DB
SNOWFLAKE_SCHEMA=RAW
SNOWFLAKE_ROLE=SYSADMIN
```

---

## Configuration Snowflake

Avant la première exécution, créer les ressources Snowflake :

```sql
USE ROLE SYSADMIN;

CREATE WAREHOUSE NYC_TAXI_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE;

CREATE DATABASE NYC_TAXI_DB;
CREATE SCHEMA NYC_TAXI_DB.RAW;
CREATE SCHEMA NYC_TAXI_DB.STAGING;
CREATE SCHEMA NYC_TAXI_DB.FINAL;
```

---

## Exécution du pipeline

### Étape 1 — Ingestion des données brutes

```bash
python python/load_datasets_to_snowflake.py
```

Le script télécharge automatiquement les fichiers mensuels depuis `https://d37ci6vzurychx.cloudfront.net/trip-data/` pour 2024 et 2025, les charge dans un stage interne Snowflake, puis exécute un `COPY INTO RAW.YELLOW_TAXI_TRIPS`.

### Étape 2 — Charger les données de référence des zones

```powershell
cd nyc_taxi_dbt

# Télécharger le fichier de référence des zones TLC
Invoke-WebRequest -Uri "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv" -OutFile "seeds/taxi_zones.csv"

# Injecter dans Snowflake
dbt seed
```

### Étape 3 — Exécuter les transformations dbt

```powershell
# Charger les variables d'environnement
Get-Content ../.env |
  Where-Object { $_ -notmatch '^\s*#' -and $_ -match '=' } |
  ForEach-Object {
    $name, $value = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), 'Process')
  }

dbt debug   # Tester la connexion
dbt run     # Construire toutes les tables
dbt test    # Lancer les tests de qualité
```

### Étape 4 — Lancer le dashboard

```bash
cd ..
python -m streamlit run dashboard.py
```

---

## Couche RAW

**Table :** `NYC_TAXI_DB.RAW.YELLOW_TAXI_TRIPS`

Données brutes des fichiers TLC sans modification, complétées par deux colonnes de métadonnées.

| Colonne | Type | Description |
|---|---|---|
| VendorID | NUMBER | Fournisseur TPEP (1, 2, 6, 7) |
| tpep_pickup_datetime | TIMESTAMP_NTZ | Date/heure de prise en charge |
| tpep_dropoff_datetime | TIMESTAMP_NTZ | Date/heure de dépose |
| passenger_count | NUMBER | Nombre de passagers |
| trip_distance | FLOAT | Distance en miles |
| RatecodeID | NUMBER | Code tarifaire |
| fare_amount | FLOAT | Tarif compteur |
| tip_amount | FLOAT | Pourboire (CB uniquement) |
| total_amount | FLOAT | Montant total facturé |
| cbd_congestion_fee | FLOAT | Péage congestion MTA (depuis jan. 2025) |
| _loaded_at | TIMESTAMP_NTZ | Horodatage de chargement |
| _source_file | VARCHAR | Nom du fichier source |

---

## Couche STAGING

**Table :** `NYC_TAXI_DB.STAGING.CLEAN_TRIPS`

Modèle dbt : [`nyc_taxi_dbt/models/staging/clean_trips.sql`](nyc_taxi_dbt/models/staging/clean_trips.sql)

### Transformations appliquées

| Catégorie | Transformation |
|---|---|
| Renommages | `tpep_pickup_datetime` → `pickup_datetime`, etc. |
| Labels métier | `vendor_name`, `payment_type_label`, `ratecode_label`, `trip_type` |
| Dimensions temporelles | `pickup_year/month/day/hour/weekday`, `time_period`, `pickup_date` |
| Flags analytiques | `is_weekend`, `is_rush_hour`, `is_airport_trip`, `has_tip`, `is_store_and_fwd` |
| Métriques calculées | `trip_duration_minutes`, `avg_speed_mph`, `tip_rate`, `distance_category` |
| Métriques financières | `total_surcharges`, `base_fare_ratio` |
| CBD Fee | `COALESCE(cbd_congestion_fee, 0)` — NULL en 2024, actif depuis jan. 2025 |

### Filtres qualité

- Année 2024–2025 uniquement
- Durée trajet : 1–300 minutes
- Distance : 0.01–200 miles
- Tarif / total : 0–500 $
- Passagers > 0
- VendorID et RatecodeID valides selon le Data Dictionary TLC 2025

---

## Couche FINAL

Toutes les tables FINAL sont matérialisées en `TABLE` dans `NYC_TAXI_DB.FINAL`.

| Table | Granularité | Métriques clés |
|---|---|---|
| `DAILY_SUMMARY` | 1 ligne / jour | Volume, revenus, tarif moyen, tip rate, % aéroport, % rush hour |
| `ZONE_ANALYSIS` | 1 ligne / zone / rôle (pickup/dropoff) | Volume, revenus, tarif, tip rate, distance, % aéroport |
| `HOURLY_PATTERNS` | 1 ligne / heure x jour de semaine | Volume, tarif, vitesse, tip rate, rush hour |
| `VENDOR_PERFORMANCE` | 1 ligne / fournisseur | Part de marché, revenus, qualité service, store-and-forward |
| `PAYMENT_ANALYSIS` | 1 ligne / mode paiement / mois | Distribution, tip rate, évolution mensuelle |
| `MONTHLY_KPI` | 1 ligne / mois | Volume, revenus, tarif, surcharges, CBD fee, indicateurs |

`taxi_zones.csv` — seed de correspondance zone_id vers nom de zone et borough (265 zones TLC).

---

## Dashboard Streamlit

**Fichier :** [`dashboard.py`](dashboard.py)

Interface analytique connectée directement à Snowflake. Navigation par section dans la sidebar, chaque section est une page scrollable.

| Section | Contenu |
|---|---|
| Accueil | KPIs globaux, vue synthétique de toutes les catégories |
| Daily Summary | Volume et revenus mensuels, top journées, weekend vs semaine |
| Zone Analysis | Top zones pickup/dropoff, déséquilibre, tarifs par zone |
| Hourly Patterns | Heatmap heure x jour, rush hour, périodes de la journée |
| Vendor Performance | Parts de marché, qualité de service, aéroport |
| Payment Analysis | Distribution des paiements, évolution CB vs Cash vs Flex Fare |
| Monthly KPI | Évolution 2024 vs 2025, impact CBD Congestion Fee |

---

## Monitoring Streamlit in Snowflake

**Fichier :** [`monitoring/pipeline_monitor.py`](monitoring/pipeline_monitor.py)

Dashboard de surveillance de la santé du pipeline, conçu pour être déployé comme application **Streamlit in Snowflake** (sans configuration de connexion : la session Snowpark est récupérée nativement via `get_active_session()`).

### Sections

| Section | Contenu |
|---|---|
| Ingestion RAW | Dernière date d'ingestion, nombre de fichiers chargés, volume total de lignes brutes |
| Qualité — RAW vs STAGING | Lignes clean_trips, lignes rejetées par les filtres qualité dbt, taux de rétention |
| Détail par fichier source | Bar chart + tableau des lignes chargées par fichier mensuel (ex : `yellow_tripdata_2024-01.parquet`) |
| Tables FINAL | Comptage de chaque table FINAL avec la cardinalité attendue en tooltip (ex : 168 lignes pour `HOURLY_PATTERNS`) |

### Déploiement dans Snowflake

1. Dans l'interface Snowflake, aller dans **Projects → Streamlit**.
2. Créer une nouvelle application Streamlit (rôle `SYSADMIN`, warehouse `NYC_TAXI_WH`, database `NYC_TAXI_DB`).
3. Copier intégralement le contenu de [`monitoring/pipeline_monitor.py`](monitoring/pipeline_monitor.py) dans l'éditeur de l'application.
4. Cliquer sur **Run** — aucun package supplémentaire ni variable d'environnement n'est nécessaire.

> **Usage local (optionnel) :** remplacer le bloc `get_active_session()` par une connexion `snowflake.connector` standard (instructions commentées en tête du fichier) puis lancer `streamlit run monitoring/pipeline_monitor.py`.

---

## CI/CD GitHub Actions

Trois workflows automatisent l'intégration, le déploiement et l'ingestion. Les credentials Snowflake sont injectés via les secrets du dépôt (`Settings → Secrets and variables → Actions`) et jamais écrits en clair dans les fichiers YAML.

**Secrets GitHub requis :**

```
SNOWFLAKE_ACCOUNT   # identifiant du compte (ex : ab12345.eu-west-1)
SNOWFLAKE_USER      # utilisateur Snowflake
SNOWFLAKE_PASSWORD  # mot de passe associé
```

> `dbt_ingestion.yml` injecte en plus `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA` et `SNOWFLAKE_ROLE` en variables d'environnement pour le script Python d'ingestion.

---

### `dbt_ci.yml` — Intégration continue (Pull Request)

**Déclencheur :** toute Pull Request ciblant `master`.

**Objectif :** valider rapidement la couche staging avant le merge, sans toucher aux tables FINAL de production.

| Étape | Action |
|---|---|
| Checkout | Clone le dépôt sur le runner Ubuntu |
| Setup Python 3.11 | Installe l'interpréteur Python sur la VM |
| Install dbt-snowflake | `pip install dbt-snowflake==1.11.5` — seul paquet nécessaire (pas de jupyter ni matplotlib) |
| dbt deps | Résout les packages déclarés dans `packages.yml` |
| dbt run — staging | `dbt run --select staging` — construit uniquement `STAGING.CLEAN_TRIPS` |
| dbt test — staging | `dbt test --select staging` — vérifie les contraintes `not_null` et `accepted_values` sur `clean_trips` |

---

### `dbt_cd.yml` — Déploiement continu (Push sur master)

**Déclencheur :** chaque push ou merge de PR sur la branche `master`.

**Objectif :** reconstruire et valider l'ensemble du pipeline dbt (toutes les couches) dès qu'une modification est intégrée.

| Étape | Action |
|---|---|
| Checkout | Clone le dépôt sur le runner Ubuntu |
| Setup Python 3.11 | Installe l'interpréteur Python sur la VM |
| Install dbt-snowflake | `pip install dbt-snowflake==1.11.5` |
| dbt deps | Résout les packages déclarés dans `packages.yml` |
| dbt run — all models | `dbt run` sans `--select` : reconstruit staging **et** les 6 tables FINAL |
| dbt test — all models | `dbt test` sur tous les modèles — échoue le workflow si un test de qualité est violé |

---

### `dbt_ingestion.yml` — ETL complet (mensuel + manuel)

**Déclencheurs :**
- **Manuel** — depuis l'onglet *Actions* du dépôt (`workflow_dispatch`).
- **Automatique** — cron `0 6 10 * *` : le 10 de chaque mois à 6h UTC (TLC publie les données du mois précédent autour de J+7/J+10).

**Objectif :** pipeline de bout en bout — téléchargement des fichiers Parquet TLC, chargement dans Snowflake, puis transformations dbt complètes.

> Ce workflow télécharge ~15 fichiers Parquet (plusieurs centaines de Mo) et tourne entre 15 et 30 minutes. Il n'est **pas** déclenché sur push pour éviter des exécutions inutiles.

| Étape | Action |
|---|---|
| Checkout | Clone le dépôt sur le runner Ubuntu |
| Setup Python 3.11 | Installe l'interpréteur Python sur la VM |
| Install Python dependencies | `pip install snowflake-connector-python requests python-dotenv` — dépendances minimales pour le script d'ingestion |
| Ingestion RAW | `python python/load_datasets_to_snowflake.py` — télécharge les fichiers TLC, les charge en stage interne Snowflake, puis `COPY INTO RAW.YELLOW_TAXI_TRIPS` (truncate + reload) |
| Install dbt-snowflake | `pip install dbt-snowflake==1.11.5` — installé après l'ingestion pour ne pas alourdir l'étape Python |
| dbt deps | Résout les packages déclarés dans `packages.yml` |
| dbt run — all models | `dbt run` sur toutes les couches (staging + final) depuis les données fraîchement chargées |
| dbt test — all models | Validation qualité globale — le workflow échoue si un test est violé |

---

## Tests de qualité dbt

Définis dans `nyc_taxi_dbt/models/staging/schema.yml` :

- `not_null` sur toutes les colonnes critiques
- `accepted_values` sur `VendorID`, `RatecodeID`, `payment_type`, `vendor_name`, `trip_type`, `time_period`, `distance_category`, `payment_type_label`, `ratecode_label`

```bash
dbt test --select clean_trips
```

---

## Requêtes analytiques

Le fichier [`nyc_taxi_dbt/analyses/queries_final.sql`](nyc_taxi_dbt/analyses/queries_final.sql) contient 40 requêtes SQL prêtes à exécuter dans Snowflake, couvrant les 6 tables FINAL :

- Top journées et évolution mensuelle
- Top zones et déséquilibre pickup/dropoff
- Patterns horaires et rush hour
- Comparaison des fournisseurs
- Distribution et évolution des modes de paiement
- Impact de la CBD Congestion Fee (jan. 2025)
- Comparaison 2024 vs 2025

---

## Sources de données

| Ressource | URL |
|---|---|
| Fichiers Parquet TLC | `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet` |
| Zones de référence | `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv` |
| Tarification TLC | `https://www.nyc.gov/site/tlc/passengers/taxi-fare.page` |
| Data Dictionary | `Docs/data_dictionary_trip_records_yellow.pdf` (mars 2025) |

---

## Equipe

Projet réalisé dans le cadre de la formation Data Engineer — Simplon.
