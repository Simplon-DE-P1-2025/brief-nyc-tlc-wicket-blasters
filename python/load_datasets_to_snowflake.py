import requests
import snowflake.connector
import tempfile
import os
from pathlib import Path
from dotenv import load_dotenv

# --- Chargement du .env ---
load_dotenv()

SNOWFLAKE_CONFIG = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
    "user":      os.getenv("SNOWFLAKE_USER"),
    "password":  os.getenv("SNOWFLAKE_PASSWORD"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "NYC_TAXI_WH"),
    "database":  os.getenv("SNOWFLAKE_DATABASE",  "NYC_TAXI_DB"),
    "schema":    os.getenv("SNOWFLAKE_SCHEMA",     "RAW"),
    "role":      os.getenv("SNOWFLAKE_ROLE",       "SYSADMIN"),
    "network_timeout": 360,
    "login_timeout":   60
}

# Vérifier que les variables critiques sont bien chargées
missing = [k for k in ("account", "user", "password") if not SNOWFLAKE_CONFIG[k]]
if missing:
    raise ValueError(f"❌ Variables manquantes dans le .env : {missing}")

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
FILES    = [(2024, m) for m in range(1, 13)] + [(2025, m) for m in range(1, 4)]

# --- Connexion ---
print("🔌 Connexion à Snowflake...")
conn   = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
cursor = conn.cursor()
print("✅ Connecté !\n")

# --- Stage ---
cursor.execute("""
    CREATE STAGE IF NOT EXISTS NYC_TAXI_DB.RAW.tlc_stage
    FILE_FORMAT = (TYPE = 'PARQUET' SNAPPY_COMPRESSION = TRUE)
""")

# --- Téléchargement + Upload ---
print(f"📦 {len(FILES)} fichiers à traiter\n")

for i, (year, month) in enumerate(FILES, 1):
    file_name = f"yellow_tripdata_{year}-{month:02d}.parquet"
    url       = f"{BASE_URL}/{file_name}"

    print(f"[{i}/{len(FILES)}] ⬇️  Téléchargement : {file_name}...")

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
        except requests.HTTPError:
            print(f"   ❌ Fichier non disponible, ignoré\n")
            os.unlink(tmp_path)
            continue

    size_mb = os.path.getsize(tmp_path) / 1_000_000
    print(f"   ⬆️  Upload vers Snowflake ({size_mb:.1f} Mo)...")

    cursor.execute(f"""
        PUT file://{tmp_path}
        @NYC_TAXI_DB.RAW.tlc_stage/{file_name}
        PARALLEL = 8
        AUTO_COMPRESS = FALSE
        OVERWRITE = FALSE
    """)

    result = cursor.fetchone()
    status = result[6] if result else "unknown"

    os.unlink(tmp_path)

    if "SKIPPED" in str(status).upper():
        print(f"   ⏭️  Déjà présent, ignoré\n")
    else:
        print(f"   ✅ Uploadé ({size_mb:.1f} Mo)\n")

# --- Vérification finale ---
cursor.execute("LIST @NYC_TAXI_DB.RAW.tlc_stage")
files_in_stage = cursor.fetchall()
total_size     = sum(f[3] for f in files_in_stage) / 1_000_000

print(f"📋 {len(files_in_stage)} fichiers dans le stage")
print(f"💾 Taille totale : {total_size:.0f} Mo")

cursor.close()
conn.close()
print("\n🎉 Terminé ! Lance CALL load_all_months() dans Snowsight.")
