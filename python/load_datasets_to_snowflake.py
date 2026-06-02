import requests
import snowflake.connector
import tempfile
import os
from dotenv import load_dotenv

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
    "network_timeout": 360,
    "login_timeout": 60
}

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
FILES = [(2024, m) for m in range(1, 13)] + [(2025, m) for m in range(1, 4)]

STAGE_NAME = "NYC_TAXI_DB.RAW.TLC_STAGE"
TABLE_NAME = "NYC_TAXI_DB.RAW.YELLOW_TAXI_TRIPS"

# ============================================================
# CONNECTION
# ============================================================

print("🔌 Connexion à Snowflake...")
conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
cursor = conn.cursor()
print("✅ Connecté\n")

# ============================================================
# CREATE STAGE (idempotent)
# ============================================================

print("📦 Création / vérification du stage...")

cursor.execute(f"""
CREATE STAGE IF NOT EXISTS {STAGE_NAME}
FILE_FORMAT = (TYPE = PARQUET)
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

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".parquet")
    
    try:
        # download
        with os.fdopen(tmp_fd, "wb") as f:
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
        print("   ⬆ upload stage...")

        cursor.execute(f"""
        PUT file://{tmp_path} @{STAGE_NAME}/{file_name}
        AUTO_COMPRESS = FALSE
        OVERWRITE = TRUE
        """)

        print("   ✅ upload OK\n")

    except requests.HTTPError:
        print("   ❌ fichier introuvable TLC\n")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# ============================================================
# COPY INTO RAW TABLE
# ============================================================

print("📥 Chargement vers table RAW...")

cursor.execute(f"""
COPY INTO {TABLE_NAME}
FROM @{STAGE_NAME}
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
ON_ERROR = CONTINUE
""")

result = cursor.fetchall()
print("✅ COPY INTO terminé")

# ============================================================
# VERIFICATION
# ============================================================

cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
count = cursor.fetchone()[0]

print(f"📊 Nombre de lignes dans RAW: {count:,}")

cursor.close()
conn.close()

print("🎉 PIPELINE TERMINÉ")