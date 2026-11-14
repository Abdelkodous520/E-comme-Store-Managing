SELECT
    COUNT(DISTINCT order_id) AS nb_commandes
FROM raw.orders
WHERE order_status NOT IN ('canceled', 'unavailable')
