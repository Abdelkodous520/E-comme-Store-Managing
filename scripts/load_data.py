
from pathlib import Path
import duckdb

# Racine du projet : dossier contenant data/ et scripts/
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data" / "raw"
DB_PATH = PROJECT_DIR / "warehouse.duckdb"

# Fichier CSV -> nom de la table dans DuckDB
FILES = {
    "olist_customers_dataset.csv": "customers",
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "olist_geolocation_dataset.csv": "geolocation",
    "product_category_name_translation.csv": "category_translation",
}

if not DATA_DIR.exists():
    raise FileNotFoundError(f"Dossier introuvable : {DATA_DIR}")

con = duckdb.connect(str(DB_PATH))
con.execute("CREATE SCHEMA IF NOT EXISTS raw")

try:
    for filename, table_name in FILES.items():
        csv_path = DATA_DIR / filename

        if not csv_path.exists():
            print(f"Fichier absent, ignoré : {filename}")
            continue

        # Échapper les apostrophes dans le chemin du fichier
        path_sql = str(csv_path.resolve()).replace("\\", "/").replace("'", "''")

        con.execute(f"""
            CREATE OR REPLACE TABLE raw.{table_name} AS
            SELECT *
            FROM read_csv_auto('{path_sql}', header = true)
        """)

        count = con.execute(
            f"SELECT COUNT(*) FROM raw.{table_name}"
        ).fetchone()[0]

        print(f"OK : raw.{table_name} -> {count:,} lignes")

    print(f"\nBase créée : {DB_PATH}")

finally:
    con.close()
