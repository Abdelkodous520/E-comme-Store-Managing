"""Construit le modèle dimensionnel Olist dans warehouse.duckdb.

Exécution : python scripts/build_star_schema.py
Les sources CSV doivent d'abord être chargées dans raw avec load_data.py.
"""
from pathlib import Path
import duckdb

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "warehouse.duckdb"

DDL = r"""
CREATE SCHEMA IF NOT EXISTS mart;

CREATE OR REPLACE TABLE mart.dim_customer AS
SELECT row_number() OVER (ORDER BY c.customer_id)::BIGINT AS customer_key,
       c.customer_id, c.customer_unique_id,
       c.customer_zip_code_prefix::VARCHAR AS postal_code,
       c.customer_city AS city, c.customer_state AS state,
       'Brazil' AS country
FROM raw.customers c;

CREATE OR REPLACE TABLE mart.dim_seller AS
SELECT row_number() OVER (ORDER BY s.seller_id)::BIGINT AS seller_key,
       s.seller_id, s.seller_zip_code_prefix::VARCHAR AS postal_code,
       s.seller_city AS city, s.seller_state AS state, 'Brazil' AS country
FROM raw.sellers s;

CREATE OR REPLACE TABLE mart.dim_product AS
SELECT row_number() OVER (ORDER BY p.product_id)::BIGINT AS product_key,
       p.product_id, p.product_category_name AS category_name_pt,
       coalesce(t.product_category_name_english, 'unknown') AS category_name_en,
       p.product_name_lenght AS name_length,
       p.product_description_lenght AS description_length,
       p.product_photos_qty AS photos_qty,
       p.product_weight_g AS weight_g, p.product_length_cm AS length_cm,
       p.product_height_cm AS height_cm, p.product_width_cm AS width_cm
FROM raw.products p
LEFT JOIN raw.category_translation t USING (product_category_name);

CREATE OR REPLACE TABLE mart.dim_date AS
WITH bounds AS (
  SELECT min(d)::DATE AS min_date, max(d)::DATE AS max_date
  FROM (SELECT order_purchase_timestamp AS d FROM raw.orders
        UNION ALL SELECT order_approved_at FROM raw.orders
        UNION ALL SELECT order_delivered_carrier_date FROM raw.orders
        UNION ALL SELECT order_delivered_customer_date FROM raw.orders
        UNION ALL SELECT order_estimated_delivery_date FROM raw.orders)
  WHERE d IS NOT NULL
), calendar AS (
  SELECT unnest(generate_series(min_date, max_date, INTERVAL 1 DAY))::DATE AS date_day
  FROM bounds
)
SELECT cast(strftime(date_day, '%Y%m%d') AS INTEGER) AS date_key,
       date_day, year(date_day) AS year, quarter(date_day) AS quarter,
       month(date_day) AS month, monthname(date_day) AS month_name,
       week(date_day) AS week_of_year, day(date_day) AS day_of_month,
       dayofweek(date_day) AS day_of_week,
       dayname(date_day) AS day_name,
       CASE WHEN dayofweek(date_day) IN (0, 6) THEN true ELSE false END AS is_weekend
FROM calendar;

-- Grain: une ligne par article d'une commande (order_id, order_item_id).
CREATE OR REPLACE TABLE mart.fact_order_items AS
SELECT oi.order_id, oi.order_item_id,
       dc.customer_key, ds.seller_key, dp.product_key,
       cast(strftime(o.order_purchase_timestamp::DATE, '%Y%m%d') AS INTEGER) AS purchase_date_key,
       cast(strftime(o.order_approved_at::DATE, '%Y%m%d') AS INTEGER) AS approved_date_key,
       cast(strftime(o.order_delivered_carrier_date::DATE, '%Y%m%d') AS INTEGER) AS carrier_date_key,
       cast(strftime(o.order_delivered_customer_date::DATE, '%Y%m%d') AS INTEGER) AS delivered_date_key,
       cast(strftime(o.order_estimated_delivery_date::DATE, '%Y%m%d') AS INTEGER) AS estimated_delivery_date_key,
       o.order_status, oi.shipping_limit_date,
       oi.price::DECIMAL(12,2) AS item_price,
       oi.freight_value::DECIMAL(12,2) AS freight_value,
       (oi.price + oi.freight_value)::DECIMAL(12,2) AS item_total,
       date_diff('day', o.order_purchase_timestamp::DATE, o.order_delivered_customer_date::DATE) AS delivery_days,
       date_diff('day', o.order_estimated_delivery_date::DATE, o.order_delivered_customer_date::DATE) AS days_vs_estimate
FROM raw.order_items oi
JOIN raw.orders o USING (order_id)
LEFT JOIN mart.dim_customer dc ON o.customer_id = dc.customer_id
LEFT JOIN mart.dim_seller ds USING (seller_id)
LEFT JOIN mart.dim_product dp USING (product_id);

-- Grain: une ligne par commande (order_id), sans duplication par article.
CREATE OR REPLACE TABLE mart.fact_orders AS
SELECT o.order_id, dc.customer_key,
       cast(strftime(o.order_purchase_timestamp::DATE, '%Y%m%d') AS INTEGER) AS purchase_date_key,
       cast(strftime(o.order_delivered_customer_date::DATE, '%Y%m%d') AS INTEGER) AS delivered_date_key,
       cast(strftime(o.order_estimated_delivery_date::DATE, '%Y%m%d') AS INTEGER) AS estimated_delivery_date_key,
       o.order_status,
       1::INTEGER AS order_count,
       date_diff('second', o.order_purchase_timestamp, o.order_delivered_customer_date) / 86400.0 AS delivery_days,
       CASE WHEN o.order_status = 'delivered'
                  AND o.order_delivered_customer_date IS NOT NULL
                  AND o.order_estimated_delivery_date IS NOT NULL
            THEN CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END
       END AS late_flag
FROM raw.orders o
LEFT JOIN mart.dim_customer dc USING (customer_id);

-- Grain: une ligne par paiement (order_id, payment_sequential).
CREATE OR REPLACE TABLE mart.fact_payments AS
SELECT p.order_id, p.payment_sequential, dc.customer_key,
       cast(strftime(o.order_purchase_timestamp::DATE, '%Y%m%d') AS INTEGER) AS purchase_date_key,
       p.payment_type, p.payment_installments,
       p.payment_value::DECIMAL(12,2) AS payment_value
FROM raw.order_payments p
JOIN raw.orders o USING (order_id)
LEFT JOIN mart.dim_customer dc ON o.customer_id = dc.customer_id;

-- Grain: une ligne par avis (review_id, order_id), sans jointure aux articles.
CREATE OR REPLACE TABLE mart.fact_reviews AS
SELECT r.review_id, r.order_id, dc.customer_key,
       cast(strftime(o.order_purchase_timestamp::DATE, '%Y%m%d') AS INTEGER) AS purchase_date_key,
       r.review_score, r.review_creation_date, r.review_answer_timestamp,
       length(r.review_comment_message) AS comment_length,
       r.review_comment_title
FROM raw.order_reviews r
JOIN raw.orders o USING (order_id)
LEFT JOIN mart.dim_customer dc ON o.customer_id = dc.customer_id;
"""

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Base introuvable : {DB_PATH}. Lancez d'abord scripts/load_data.py")
    con = duckdb.connect(str(DB_PATH))
    try:
        missing = con.execute("""SELECT count(*) FROM (VALUES
          ('customers'), ('orders'), ('order_items'), ('order_payments'),
          ('order_reviews'), ('products'), ('sellers'), ('category_translation')) v(name)
          WHERE NOT EXISTS (SELECT 1 FROM information_schema.tables t
            WHERE t.table_schema='raw' AND t.table_name=v.name)""").fetchone()[0]
        if missing:
            raise RuntimeError("Tables raw manquantes : exécutez scripts/load_data.py d'abord.")
        con.execute(DDL)
        for table, in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='mart' ORDER BY 1").fetchall():
            n = con.execute(f'SELECT count(*) FROM mart."{table}"').fetchone()[0]
            print(f"mart.{table}: {n:,} lignes")
        print(f"\nEntrepôt mis à jour : {DB_PATH}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
