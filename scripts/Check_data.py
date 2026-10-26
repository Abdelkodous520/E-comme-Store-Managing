
from pathlib import Path
import duckdb

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "warehouse.duckdb"

if not DB_PATH.exists():
    raise FileNotFoundError(
        f"Base DuckDB introuvable : {DB_PATH}"
    )

con = duckdb.connect(str(DB_PATH), read_only=True)

try:
    # Lister les tables du schéma raw
    tables = con.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'raw'
        ORDER BY table_name
    """).fetchall()

    print("=== TABLES CHARGEES ===")
    if not tables:
        print("Aucune table trouvée dans le schéma raw.")

    for (table_name,) in tables:
        count = con.execute(
            f'SELECT COUNT(*) FROM raw."{table_name}"'
        ).fetchone()[0]

        print(f"{table_name}: {count:,} lignes")

    # Examiner la structure de la table customers
    print("\n=== COLONNES DE raw.customers ===")
    exists = any(name == "customers" for (name,) in tables)

    if exists:
        columns = con.execute("""
            DESCRIBE SELECT * FROM raw.customers
        """).fetchall()

        for column in columns:
            print(f"{column[0]} ({column[1]})")

        print("\n=== APERCU DES CLIENTS ===")
        print(
            con.execute("""
                SELECT *
                FROM raw.customers
                LIMIT 5
            """).df().to_string(index=False)
        )
    else:
        print("La table raw.customers est absente.")

finally:
    con.close()
