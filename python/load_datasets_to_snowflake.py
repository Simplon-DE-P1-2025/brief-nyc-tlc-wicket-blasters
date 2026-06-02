import requests
import snowflake.connector
import tempfile
import os
import shutil
import logging
from dotenv import load_dotenv

# ============================================================
# LOGGING
# ============================================================

logging.getLogger("snowflake.connector").setLevel(logging.WARNING)

# ============================================================
# CONFIG
# ============================================================

load_dotenv()

SNOWFLAKE_CONFIG = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
    "user":      os.getenv("SNOWFLAKE_USER"),
    "password":  os.getenv("SNOWFLAKE_PASSWORD"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "NYC_TAXI_WH"),
    "database":  os.getenv("SNOWFLAKE_DATABASE", "NYC_TAXI_DB"),
    "schema":    os.getenv("SNOWFLAKE_SCHEMA", "RAW"),
    "role":      os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
    "network_timeout": 900,
    "login_timeout": 60
}

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
FILES = [(2024, m) for m in range(1, 13)] + [(2025, m) for m in range(1, 4)]

STAGE_NAME = "NYC_TAXI_DB.RAW.TLC_STAGE"
TABLE_NAME = "NYC_TAXI_DB.RAW.YELLOW_TAXI_TRIPS"

FILE_FORMAT = "(TYPE = PARQUET USE_LOGICAL_TYPE = TRUE)"

# ============================================================
# CONNECTION
# ============================================================

print("🔌 Connexion à Snowflake...")
conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
cursor = conn.cursor()
print("✅ Connecté\n")

# ============================================================
# CLEANUP : TRUNCATE TABLE + PURGE STAGE
# ============================================================

print("🗑️ Truncate table RAW...")
cursor.execute(f"TRUNCATE TABLE IF EXISTS {TABLE_NAME}")
print("✅ Table vidée")

print("🗑️ Purge du stage...")
cursor.execute(f"REMOVE @{STAGE_NAME}")
print("✅ Stage vidé\n")

# ============================================================
# CREATE STAGE (idempotent)
# ============================================================

print("📦 Création / vérification du stage...")

cursor.execute(f"""
CREATE STAGE IF NOT EXISTS {STAGE_NAME}
FILE_FORMAT = {FILE_FORMAT}
COMMENT = 'Stage interne NYC Taxi'
""")

print("✅ Stage OK\n")

# ============================================================
# UPLOAD FILES TO STAGE
# ============================================================

print(f"🚕 {len(FILES)} fichiers à traiter\n")

for i, (year, month) in enumerate(FILES, 1):

    file_name = f"yellow_tripdata_{year}-{month:02d}.parquet"
    url = f"{BASE_URL}/{file_name}"

    print(f"[{i}/{len(FILES)}] 📥 {file_name}")

    # FIX : dossier temp + nom de fichier explicite (au lieu de mkstemp)
    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, file_name)

    try:
        # download
        with open(tmp_path, "wb") as f:
            r = requests.get(url, stream=True)
            r.raise_for_status()

            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = os.path.getsize(tmp_path) / 1_000_000
        print(f"   ✔ téléchargé ({size_mb:.1f} MB)")

        if size_mb < 1:
            print("   ⚠ fichier trop petit, skip\n")
            continue

        # upload stage
        # FIX : PUT vers @STAGE sans sous-dossier → le fichier garde son nom
        print("   ⬆ upload stage...")

        cursor.execute(f"""
        PUT file://{tmp_path} @{STAGE_NAME}
        AUTO_COMPRESS = FALSE
        OVERWRITE = TRUE
        """)

        print("   ✅ upload OK\n")

    except requests.HTTPError:
        print("   ❌ fichier introuvable TLC\n")

    finally:
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)

# ============================================================
# COPY INTO RAW TABLE (fichier par fichier + métadonnées)
# ============================================================

print("📥 Chargement vers table RAW...\n")

cursor.execute(f"LIST @{STAGE_NAME}")
staged_files = cursor.fetchall()

for row in staged_files:
    staged_path = row[0]
    file_name = staged_path.split("/")[-1]

    print(f"   📄 COPY {file_name}...")

    cursor.execute(f"""
    COPY INTO {TABLE_NAME}
    FROM @{STAGE_NAME}/{file_name}
    FILE_FORMAT = (TYPE = PARQUET USE_LOGICAL_TYPE = TRUE)
    MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
    ON_ERROR = CONTINUE
    """)

    # Remplir les métadonnées pour les lignes qui viennent d'être chargées
    cursor.execute(f"""
    UPDATE {TABLE_NAME}
    SET _SOURCE_FILE = '{file_name}',
        _LOADED_AT   = CURRENT_TIMESTAMP()
    WHERE _SOURCE_FILE IS NULL
    """)

    print(f"   ✅ {file_name} chargé + métadonnées OK")

print("\n✅ Chargement terminé\n")

# ============================================================
# VERIFICATION
# ============================================================

cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
count = cursor.fetchone()[0]

print(f"📊 Nombre de lignes dans RAW: {count:,}")

cursor.close()
conn.close()

print("🎉 PIPELINE TERMINÉ")