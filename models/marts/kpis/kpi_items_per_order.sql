
{{ config(materialized='view') }}

WITH commandes AS (

    SELECT
        order_id,
        SUM(item_count) AS nb_articles

    FROM {{ ref('fact_order_lines') }}

    WHERE order_status NOT IN ('canceled', 'unavailable')

    GROUP BY order_id

    HAVING SUM(item_count) > 0

)

SELECT
    ROUND(
        CAST(SUM(nb_articles) AS DOUBLE)
        / COUNT(*),
        2
    ) AS articles_moyens_par_commande,

    SUM(nb_articles) AS nb_total_articles,

    COUNT(*) AS nb_commandes_avec_articles

FROM commandes
