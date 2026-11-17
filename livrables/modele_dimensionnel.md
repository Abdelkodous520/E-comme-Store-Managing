# Modèle dimensionnel Olist (DuckDB)

La base physique est `warehouse.duckdb`. Les CSV d'origine sont chargés dans le schéma `raw`; le script `scripts/build_star_schema.py` construit les tables analytiques dans `mart`.

## Schéma en étoile proposé

Le modèle comporte exactement quatre tables de faits complémentaires, chacune conservant son propre grain : `FACT_REVIEWS`, `FACT_PAYMENTS`, `FACT_ORDER_ITEMS` et `FACT_ORDERS`. `FACT_ORDER_ITEMS` est au grain **une ligne par article de commande** (`order_id`, `order_item_id`) et porte les montants et les clés de produit/vendeur. `FACT_ORDERS` est au grain **une ligne par commande** (`order_id`) et porte le statut, le délai et le retard calculés une seule fois par commande. `FACT_PAYMENTS` décrit une ligne par paiement séquentiel et `FACT_REVIEWS` une ligne par avis source. Les dimensions partagées décrivent le client et les dates; les articles ajoutent produit et vendeur. Les dates réutilisent `dim_date` selon leurs rôles.

`FACT_PAYMENTS` et `FACT_REVIEWS` partagent les dimensions client et date d'achat. Pour analyser paiements ou avis avec les articles, agréger chaque fait au niveau commande avant de les joindre.

```text
                         dim_date (rôles: achat, approbation,
                         expédition, livraison, estimation)
                                      |
dim_customer ---- fact_order_items ---- dim_product
                       |
                   dim_seller

dim_customer ---- fact_orders ---- dim_date (achat/livraison/estimation)

dim_customer ---- fact_payments ---- dim_date (achat)
dim_customer ---- fact_reviews  ---- dim_date (achat)
```

## Tables

| Table | Grain / clé de grain | Contenu |
|---|---|---|
| `mart.dim_customer` | un client de commande (`customer_id`) | identifiant client unique et localisation |
| `mart.dim_seller` | un vendeur (`seller_id`) | localisation vendeur |
| `mart.dim_product` | un produit (`product_id`) | catégorie portugaise et traduction anglaise, caractéristiques |
| `mart.dim_date` | un jour (`date_key`) | attributs calendaires |
| `FACT_ORDER_ITEMS` | une ligne article (`order_id`, `order_item_id`) | prix, fret et clés produit/vendeur |
| `FACT_ORDERS` | une commande (`order_id`) | statut, durée de livraison, indicateur de retard; une ligne par commande |
| `FACT_PAYMENTS` | un paiement (`order_id`, `payment_sequential`) | type, échéances, montant |
| `FACT_REVIEWS` | un avis source (`review_id`, `order_id`) | note, dates et longueur de commentaire |

## Hiérarchies analytiques

- **Temps** : année → trimestre → mois → semaine → jour. Pour les rapports mensuels, privilégier année → mois afin d'éviter de mélanger des mois de différentes années.
- **Géographie client** : pays → état (UF) → ville → code postal. Même hiérarchie côté vendeur. Le pays est constant (« Brazil ») dans ce dataset.
- **Produit** : catégorie (libellé anglais traduit) → produit. Les caractéristiques produit (poids, dimensions, photos) sont des attributs descriptifs, pas des niveaux de hiérarchie.
- **Commande** : état de commande est un axe de regroupement plat; le jeu de données ne fournit pas de niveaux parent/enfant métier supplémentaires.
- **Paiement** : type de paiement → nombre d'échéances; ce sont des axes descriptifs, pas une hiérarchie stricte.

Les clés métier d'origine sont conservées. Les clés `customer_key`, `seller_key` et `product_key` sont des clés substituts générées à la reconstruction. `dim_date.date_key` est au format `AAAAMMJJ`.

## Construction

1. `python scripts/load_data.py` charge ou recharge les fichiers dans `raw`.
2. `python scripts/build_star_schema.py` (dans l'environnement virtuel du projet si nécessaire) reconstruit les tables `mart` dans `warehouse.duckdb`.

Les tables `raw` sont conservées. Le script peut être relancé après mise à jour des sources.
