
{{ config(materialized='view') }}

WITH commandes AS (

    SELECT
        order_id,
        SUM(freight_value) AS frais_livraison

    FROM {{ ref('fact_order_items') }}

    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND item_count = 1

    GROUP BY order_id

)

SELECT
    ROUND(AVG(frais_livraison), 2)
        AS frais_livraison_moyens_brl,

    ROUND(SUM(frais_livraison), 2)
        AS total_frais_livraison,

    COUNT(*) AS nb_commandes_avec_articles

FROM commandes
