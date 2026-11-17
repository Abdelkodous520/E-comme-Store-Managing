
{{ config(materialized='view') }}

SELECT
    ROUND(
        AVG(duree_livraison_jours),
        2
    ) AS delai_moyen_jours,

    COUNT(duree_livraison_jours)
        AS nb_commandes_evaluees

FROM {{ ref('fact_orders') }}

WHERE order_status = 'delivered'
  AND duree_livraison_jours IS NOT NULL
