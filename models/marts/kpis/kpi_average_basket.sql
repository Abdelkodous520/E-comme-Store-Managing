
{{ config(materialized='view') }}

WITH commandes AS (

    SELECT
        order_id,
        SUM(price) AS valeur_articles

    FROM {{ ref('fact_order_lines') }}

    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND item_count = 1

    GROUP BY order_id

)

SELECT
    ROUND(AVG(valeur_articles), 2)
        AS panier_moyen_brl,

    COUNT(*) AS nb_commandes_avec_articles

FROM commandes
