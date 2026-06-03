# NYC TLC

## GitHub Actions

Trois workflows automatisent le pipeline de données. Ils sont définis dans `.github/workflows/`.

---

### 1. CI — Validation staging (`dbt_ci.yml`)

**Déclencheur :** ouverture ou mise à jour d'une Pull Request vers `master`

**Rôle :** valide que les modèles de la couche staging sont corrects avant tout merge. Sert de filet de sécurité pour le travail collaboratif.

**Étapes :**
1. Installation de `dbt-snowflake`
2. `dbt deps` — installation des packages dbt
3. `dbt run --select staging` — construction des modèles staging uniquement
4. `dbt test --select staging` — exécution des tests de qualité (not_null, accepted_values…)

---

### 2. CD — Déploiement complet (`dbt_cd.yml`)

**Déclencheur :** push ou merge sur `master`

**Rôle :** reconstruit toutes les couches dbt (staging + final) après chaque merge validé. Maintient Snowflake à jour en continu.

**Étapes :**
1. Installation de `dbt-snowflake`
2. `dbt deps`
3. `dbt run` — construction de tous les modèles (staging + final)
4. `dbt test` — validation qualité sur l'ensemble des modèles

---

### 3. ETL complet — Ingestion + DBT (`dbt_ingestion.yml`)

**Déclencheur :**
- Manuel depuis l'onglet **Actions** → **Run workflow**
- Automatique le **10 de chaque mois à 6h UTC** (les fichiers du mois précédent sont publiés par TLC autour du J+7/J+10)

**Rôle :** pipeline complet de bout en bout. Télécharge les fichiers Parquet depuis la source NYC TLC, charge les données brutes dans Snowflake (couche RAW), puis déclenche les transformations dbt.

**Étapes :**
1. Installation des dépendances Python (`snowflake-connector-python`, `requests`, `python-dotenv`)
2. Exécution du script `python/load_datasets_to_snowflake.py` — téléchargement + chargement dans `RAW.yellow_taxi_trips`
3. Installation de `dbt-snowflake`
4. `dbt deps`
5. `dbt run` — transformations staging + final
6. `dbt test` — validation qualité

> **Note :** ce workflow truncate la table RAW avant de recharger. Durée estimée : 15-30 minutes.

---

### Secrets requis

Les trois workflows utilisent les secrets suivants, à configurer dans **Settings → Secrets and variables → Actions** :

| Secret | Description |
|---|---|
| `SNOWFLAKE_ACCOUNT` | Identifiant du compte Snowflake |
| `SNOWFLAKE_USER` | Nom d'utilisateur |
| `SNOWFLAKE_PASSWORD` | Mot de passe |