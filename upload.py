import snowflake.connector
from pathlib import Path
import time

# --- Configuration ---
SNOWFLAKE_CONFIG = {
    "account":   "ton_account_identifier",
    "user":      "ton_username",
    "password":  "ton_password",
    "warehouse": "NYC_TAXI_WH",
    "database":  "NYC_TAXI_DB",
    "schema":    "RAW",
    "role":      "SYSADMIN"
}

DATA_DIR = Path("nyc_taxi_data")

# --- Connexion ---
print("🔌 Connexion à Snowflake...")
conn = snowflake.connector.connect(
    **SNOWFLAKE_CONFIG,
    network_timeout=360,      # timeout réseau élevé pour les gros fichiers
    login_timeout=60
)
cursor = conn.cursor()
print("✅ Connecté !\n")

# --- Stage ---
cursor.execute("""
    CREATE STAGE IF NOT EXISTS NYC_TAXI_DB.RAW.tlc_stage
    FILE_FORMAT = (TYPE = 'PARQUET' SNAPPY_COMPRESSION = TRUE)
""")

# --- Upload ---
parquet_files = sorted(DATA_DIR.glob("*.parquet"))
print(f"📦 {len(parquet_files)} fichiers à uploader\n")

for i, file_path in enumerate(parquet_files, 1):
    size_mb = file_path.stat().st_size / 1_000_000
    print(f"[{i}/{len(parquet_files)}] ⬆️  {file_path.name} ({size_mb:.1f} Mo)...")

    start = time.time()

    cursor.execute(f"""
        PUT file://{file_path.absolute()}
        @NYC_TAXI_DB.RAW.tlc_stage
        PARALLEL = 8          -- threads parallèles pour les gros fichiers
        AUTO_COMPRESS = FALSE  -- déjà en Parquet/Snappy, pas besoin de recompresser
        OVERWRITE = FALSE      -- ne pas re-uploader si déjà présent
    """)

    result = cursor.fetchone()
    elapsed = time.time() - start
    status = result[6] if result else "unknown"  # colonne STATUS du PUT

    if "UPLOADED" in str(status).upper():
        print(f"   ✅ Uploadé en {elapsed:.1f}s")
    elif "SKIPPED" in str(status).upper():
        print(f"   ⏭️  Déjà présent, ignoré")
    else:
        print(f"   ⚠️  Statut : {status}")

# --- Vérification finale ---
print("\n📋 Vérification du stage...")
cursor.execute("LIST @NYC_TAXI_DB.RAW.tlc_stage")
files_in_stage = cursor.fetchall()
print(f"✅ {len(files_in_stage)} fichiers dans le stage\n")

total_size = sum(f[3] for f in files_in_stage) / 1_000_000
print(f"💾 Taille totale dans le stage : {total_size:.0f} Mo")

cursor.close()
conn.close()
print("\n🎉 Upload terminé ! Lance CALL load_all_months() dans Snowsight.")
