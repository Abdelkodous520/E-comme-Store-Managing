
{{ config(materialized='view') }}

SELECT
    COUNT(*) AS nb_lignes_avis,

    COUNT(*) FILTER (
        WHERE review_score >= 4
    ) AS nb_avis_positifs,

    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE review_score >= 4
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS taux_satisfaction_pct

FROM {{ ref('fact_reviews') }}

WHERE review_score BETWEEN 1 AND 5
