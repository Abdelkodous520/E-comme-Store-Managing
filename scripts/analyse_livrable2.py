"""Analyse read-only Olist et génération du livrable PDF (4 pages max).

Dépendances déjà présentes dans l'environnement : duckdb, matplotlib.
Exécution depuis la racine : python scripts/analyse_livrable2.py
"""
from pathlib import Path
import json
import textwrap
import tempfile
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "warehouse.duckdb"
OUT = ROOT / "livrables"
OUT.mkdir(exist_ok=True)
PREVIEW = Path(tempfile.gettempdir()) / "livrable2_visual_check"
PREVIEW.mkdir(exist_ok=True)
_TEXT_PAGE = 0

def analyze():
    con = duckdb.connect(str(DB), read_only=True)
    result = {"tables": {}, "quality": {}, "metrics": {}}
    try:
        names = [r[0] for r in con.execute("select table_name from information_schema.tables where table_schema='raw' order by 1").fetchall()]
        result["raw_tables"] = names
        for t in names:
            cols = con.execute(f'DESCRIBE SELECT * FROM raw."{t}"').fetchall()
            n = con.execute(f'SELECT count(*) FROM raw."{t}"').fetchone()[0]
            result["tables"][t] = {"rows": n, "columns": [{"name": c[0], "type": c[1]} for c in cols]}
        queries = {
          "orders_status": "select order_status, count(*) n from raw.orders group by 1 order by 1",
          "orders_nulls": "select count(*) total, count(*) filter(where order_delivered_customer_date is null) delivery_customer_null, count(*) filter(where order_delivered_carrier_date is null) carrier_null, count(*) filter(where order_estimated_delivery_date is null) estimate_null from raw.orders",
          "orders_dups": "select count(*)-count(distinct order_id) duplicates from raw.orders",
          "items_key": "select count(*) n, count(*)-count(distinct (order_id,order_item_id)) duplicates from raw.order_items",
          "payments_key": "select count(*) n, count(distinct order_id) orders, count(*)-count(distinct (order_id, payment_sequential)) duplicates from raw.order_payments",
          "reviews": "select count(*) n, count(distinct review_id) review_ids, count(distinct order_id) orders, count(*)-count(distinct review_id) duplicate_review_ids from raw.order_reviews",
          "reviews_multi": "select count(*) from (select order_id from raw.order_reviews group by 1 having count(*)>1)",
          "review_id_repeated_groups": "select count(*) from (select review_id from raw.order_reviews group by 1 having count(*)>1)",
          "review_exact_duplicate_rows": "select count(*)-count(distinct (review_id,order_id,review_score,review_comment_title,review_comment_message,review_creation_date,review_answer_timestamp)) from raw.order_reviews",
          "customers": "select count(*) n, count(distinct customer_id) ids, count(distinct customer_unique_id) unique_people from raw.customers",
          "repeat_rate": "with per_person as (select c.customer_unique_id, count(distinct o.order_id) n_orders from raw.orders o join raw.customers c using(customer_id) where o.order_status not in ('canceled','unavailable') group by 1), agg as (select count(*) people, count(*) filter(where n_orders>=2) repeat_people from per_person) select people, repeat_people, repeat_people*100.0/nullif(people,0) rate_percent from agg",
          "eligible_orders": "select count(distinct order_id) from raw.orders where order_status not in ('canceled','unavailable')",
          "eligible_orders_without_items": "select count(*) from raw.orders o where o.order_status not in ('canceled','unavailable') and not exists (select 1 from raw.order_items i where i.order_id=o.order_id)",
          "eligible_orders_with_items": "select count(distinct o.order_id) from raw.orders o join raw.order_items i using(order_id) where o.order_status not in ('canceled','unavailable')",
          "products_nullcat": "select count(*) filter(where product_category_name is null) n, count(*) total from raw.products",
          "geo": "select count(*) n, count(distinct (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng)) distinct_points, count(distinct geolocation_zip_code_prefix) zips from raw.geolocation",
          "order_item_orphans": "select count(*) from raw.order_items i left join raw.orders o using(order_id) where o.order_id is null",
          "payment_orphans": "select count(*) from raw.order_payments p left join raw.orders o using(order_id) where o.order_id is null",
          "items_orphans": "select count(*) from raw.order_items i left join raw.products p using(product_id) where p.product_id is null",
          "seller_orphans": "select count(*) from raw.order_items i left join raw.sellers s using(seller_id) where s.seller_id is null",
          "orders_without_items": "select count(*) from raw.orders o left join raw.order_items i using(order_id) where i.order_id is null",
          "orders_without_payments": "select count(*) from raw.orders o left join raw.order_payments p using(order_id) where p.order_id is null",
          "dimension_key_duplicates": "select (select count(*)-count(distinct product_id) from raw.products) product_id_extra, (select count(*)-count(distinct seller_id) from raw.sellers) seller_id_extra, (select count(*)-count(distinct customer_id) from raw.customers) customer_id_extra",
          "item_sales": "select sum(i.price) gross_merchandise, sum(i.freight_value) freight, count(distinct i.order_id) orders from raw.order_items i join raw.orders o using(order_id) where o.order_status not in ('canceled','unavailable')",
          "datedel": "select count(*) filter(where order_delivered_customer_date is not null and order_purchase_timestamp is not null) delivered_with_dates, avg(date_diff('day', order_purchase_timestamp, order_delivered_customer_date)) filter(where order_delivered_customer_date is not null and order_purchase_timestamp is not null) avg_days, count(*) filter(where order_delivered_customer_date > order_estimated_delivery_date) late from raw.orders where order_status='delivered'",
          "delivery_date_controls": "select count(*) filter(where order_status='delivered' and order_delivered_customer_date is not null and order_estimated_delivery_date is not null) evaluable, count(*) filter(where order_status='delivered' and order_delivered_customer_date > order_estimated_delivery_date) late, count(*) filter(where order_status='delivered' and order_delivered_customer_date < order_purchase_timestamp) negative_duration, count(*) filter(where order_status='delivered' and order_delivered_customer_date is not null and order_delivered_carrier_date is not null and order_delivered_customer_date < order_delivered_carrier_date) customer_before_carrier, count(*) filter(where order_status='delivered' and order_delivered_carrier_date < order_purchase_timestamp) carrier_before_purchase from raw.orders",
          "review_stats": "select avg(review_score) filter(where review_score between 1 and 5), count(*) filter(where review_score between 4 and 5)*1.0/nullif(count(*) filter(where review_score between 1 and 5),0) from raw.order_reviews",
          "review_score_invalid": "select count(*) filter(where review_score is null or review_score not between 1 and 5) from raw.order_reviews",
          "gmv_by_status": "select o.order_status, sum(i.price) gmv_items from raw.orders o join raw.order_items i using(order_id) group by 1 order by 1",
          "gmv_delivered": "select sum(i.price) gmv_items, count(distinct o.order_id) orders from raw.orders o join raw.order_items i using(order_id) where o.order_status='delivered'",
        }
        for k,q in queries.items():
            val=con.execute(q).fetchall()
            result["quality"][k] = val
        def one(key):
            return result["quality"][key][0] if result["quality"][key] else None
        result["metrics"] = {
            "orders_admissible": one("eligible_orders")[0],
            "eligible_orders_without_items": one("eligible_orders_without_items")[0],
            "eligible_orders_with_items": one("eligible_orders_with_items")[0],
            "repeat_customers": {"denominator_people": one("repeat_rate")[0], "numerator_people": one("repeat_rate")[1], "rate_percent": one("repeat_rate")[2]},
            "gmv_admissible_items_brl": one("item_sales")[0],
            "basket_mean_all_eligible_brl": one("item_sales")[0] / one("eligible_orders")[0],
            "basket_mean_with_items_brl": one("item_sales")[0] / one("eligible_orders_with_items")[0],
            "freight_admissible_brl": one("item_sales")[1],
            "gmv_delivered_items_brl": one("gmv_delivered")[0],
            "delivered_order_count": one("gmv_delivered")[1],
            "delivery_evaluable_count": one("delivery_date_controls")[0],
            "late_delivered_count": one("delivery_date_controls")[1],
            "late_rate_percent": one("delivery_date_controls")[1] * 100 / one("delivery_date_controls")[0] if one("delivery_date_controls")[0] else None,
            "avg_delivery_days": one("datedel")[1],
            "negative_delivery_durations": one("delivery_date_controls")[2],
            "review_avg_score": one("review_stats")[0],
            "review_satisfaction_percent": one("review_stats")[1] * 100 if one("review_stats")[1] is not None else None,
            "valid_review_count": one("reviews")[0] - one("review_score_invalid")[0],
        }
        # Null count for every source field
        result["nulls"] = {}
        for t in names:
            fields=[r["name"] for r in result["tables"][t]["columns"]]
            expr=", ".join(f'count(*) filter(where "{c}" is null)' for c in fields)
            result["nulls"][t]=dict(zip(fields,con.execute(f'SELECT {expr} FROM raw."{t}"').fetchone()))
        return result
    finally:
        con.close()

def box(ax, xy, w, h, title, body, color):
    x,y=xy
    p=FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.012,rounding_size=0.018",facecolor=color,edgecolor="#29465b",linewidth=1.2)
    ax.add_patch(p)
    ax.text(x+w/2,y+h-.04,title,ha="center",va="top",fontsize=9.3,fontweight="bold",color="#102a43")
    ax.text(x+.018,y+h-.09,body,ha="left",va="top",fontsize=7.4,color="#243b53",linespacing=1.25)

def make_star(path):
    fig,ax=plt.subplots(figsize=(11.7,8.3)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
    ax.set_title("Schéma dimensionnel — constellation de faits et rôles des clés",fontsize=16,fontweight="bold",pad=14,color="#102a43")
    box(ax,(.32,.39),.30,.27,"FACT_ORDER_ITEMS · grain : ligne d’article","PK (order_id, order_item_id)\nFK product_key, seller_key, customer_key, date_key\nprice, freight_value (séparés), quantité (=1)\norder_id = commande ; customer_id source → customer_key","#d9edf7")
    box(ax,(.66,.43),.30,.25,"FACT_ORDERS · grain : commande","PK order_id · FK customer_key (1 client → N commandes)\nFK date_achat_key, date_livraison_key, date_estimee_key\nstatus ; order_count=1, durée, retard\nLes 3 clés de date pointent vers DIM_DATE","#fce8d5")
    box(ax,(.66,.76),.30,.15,"FACT_PAYMENTS · grain : séquence de paiement","PK (order_id, payment_sequential) · FK order_id\npayment_value, payment_installments, payment_type\nGarder à part ; agréger par commande avant rapprochement","#fff2cc")
    box(ax,(.66,.10),.30,.17,"FACT_REVIEWS · grain : ligne source d’avis","PK review_row_key à générer au modèle final\nreview_id non unique ; FK order_id, review_date_key\nreview_date_key = review_creation_date ; garder les lignes","#fff2cc")
    box(ax,(.02,.67),.23,.17,"DIM_PRODUCT","PK product_key · BK product_id\nCatégorie/traduction, dimensions\nProduit → catégorie","#e4f3e6")
    box(ax,(.02,.37),.23,.17,"DIM_SELLER","PK seller_key · BK seller_id\nVille → état ; région indisponible","#e4f3e6")
    box(ax,(.32,.08),.30,.23,"DIM_CUSTOMER","PK customer_key = clé substitut\ncustomer_id = client associé à la commande (BK)\ncustomer_unique_id = personne entre commandes\nVille → état ; région non disponible","#e4f3e6")
    box(ax,(.32,.75),.30,.18,"DIM_DATE · dimension à rôles","PK date_key (YYYYMMDD)\nDate → mois → trimestre → année\nRôles : achat, réelle, estimée, création avis","#e4f3e6")
    # Arrows are foreign-key directions; order_id links are explicitly 1-to-many.
    for a,b in [((.25,.75),(.32,.57)),((.25,.45),(.32,.49)),((.47,.31),(.47,.39)),((.47,.75),(.47,.66)),((.62,.80),(.66,.64)),((.81,.68),(.81,.76)),((.81,.43),(.81,.27))]:
        ax.annotate("",xy=b,xytext=a,arrowprops=dict(arrowstyle="->",color="#627d98",lw=1.25))
    # Separate gutter routes keep the customer-to-orders and date-to-reviews links visible.
    ax.plot([.62,.65,.65],[.29,.29,.40],color="#627d98",lw=1.25)
    ax.annotate("",xy=(.67,.43),xytext=(.65,.40),arrowprops=dict(arrowstyle="->",color="#627d98",lw=1.25))
    ax.plot([.62,.635,.635],[.77,.77,.30],color="#627d98",lw=1.25)
    ax.annotate("",xy=(.67,.24),xytext=(.635,.30),arrowprops=dict(arrowstyle="->",color="#627d98",lw=1.25))
    fig.text(.5,.015,"DIM_DATE role-playing : achat, livraison réelle, livraison estimée, création d’avis. FK order_id relie les faits paiement/avis à la commande ; agréger avant rapprochement aux articles. payment_type reste attribut de filtre.",ha="center",fontsize=8,color="#486581")
    fig.savefig(path,dpi=180,bbox_inches="tight"); return fig

def page_text(pdf, title, blocks, fontsize=10):
    global _TEXT_PAGE
    _TEXT_PAGE += 1
    fig=plt.figure(figsize=(8.27,11.69)); ax=fig.add_axes([.08,.06,.84,.88]); ax.axis("off")
    fig.text(.08,.955,title,fontsize=18,fontweight="bold",color="#102a43")
    y=.91
    for head,body in blocks:
        ax.text(0,y,head,fontsize=11,fontweight="bold",color="#126782",va="top"); y-=.027
        width=max(65,int(105*10/fontsize))
        wrapped="\n".join(textwrap.wrap(body,width=width,break_long_words=False))
        lines=wrapped.count("\n")+1
        ax.text(0,y,wrapped,fontsize=fontsize,color="#243b53",va="top",linespacing=1.28); y-=.023*(lines*fontsize/10)+.014
    if y < .02:
        raise ValueError(f"Texte débordant sur la page {title!r}: marge basse={y:.3f}")
    fig.savefig(PREVIEW/f"page_texte_{_TEXT_PAGE}.png",dpi=110)
    pdf.savefig(fig); plt.close(fig)

def page_kpis(pdf, data):
    fig=plt.figure(figsize=(8.27,11.69)); ax=fig.add_axes([.045,.045,.91,.90]); ax.axis("off")
    m=data["metrics"]
    basket_items=f"{m['basket_mean_with_items_brl']:.2f}".replace(".",",")
    basket_all=f"{m['basket_mean_all_eligible_brl']:.2f}".replace(".",",")
    fig.text(.055,.958,"KPI | Définitions, formules et décisions",fontsize=17,fontweight="bold",color="#102a43")
    fig.text(.055,.928,"Commerce : hors canceled/unavailable. Logistique : commandes livrées avec dates requises.",fontsize=8.2,color="#486581")
    rows=[
      ["1 · GMV articles","Σ price ; commandes admissibles. GMV livré : même somme, status='delivered'. Hors freight_value, paiement, coûts et marge.","Achat, catégorie, vendeur, client, zone","Arbitrer assortiment et ventes ; comparer GMV admissible au GMV livré."],
      ["2 · Nombre de commandes","COUNT(DISTINCT order_id) ; statuts admissibles, depuis orders.","Date achat, statut, client, zone","Suivre la demande sans compter articles ni paiements."],
      ["3 · Panier moyen",f"Principal : GMV / COUNT DISTINCT admissibles avec ≥1 article = {basket_items} BRL. Comparaison : diviser par toutes les admissibles = {basket_all} BRL.","Mois achat, catégorie, zone","Montant acheté par commande avec articles ; le ratio alternatif inclut celles sans article."],
      ["4 · GMV par catégorie","Σ order_items.price par catégorie ; commandes admissibles.","Catégorie, mois, vendeur","Identifier catégories à développer ou à surveiller."],
      ["5 · GMV par vendeur","Σ order_items.price par seller_id ; commandes admissibles.","Vendeur, état, mois","Comparer la contribution et prioriser l’accompagnement vendeur."],
      ["6 · Délai moyen de livraison","AVG(delivered_customer_date − purchase_timestamp) ; status='delivered', dates réelles présentes.","Mois d’achat, état client, vendeur via attribution commande","Repérer périodes et zones où le parcours logistique ralentit."],
      ["7 · Livraison en retard","100 × COUNT(commandes livrées après estimated_delivery_date) / COUNT(commandes livrées avec date réelle + estimée) ; statut delivered.","Mois d’achat, état, vendeur via commande","Cibler les transporteurs/zones et réduire les retards."],
      ["8 · Note moyenne des avis","AVG(review_score), scores valides 1–5 ; grain ligne source d’avis, tous statuts.","Date de création, score, client/zone via commande","Détecter l’évolution de l’expérience client."],
      ["9 · Taux de satisfaction","100 × COUNT(score 4–5) / COUNT(score 1–5) ; grain ligne source d’avis.","Date de création, score, zone/catégorie après agrégat","Suivre la part d’avis positifs et prioriser les irritants."],
      ["10 · Clients récurrents","100 × COUNT(personnes avec ≥2 commandes) / COUNT(personnes avec ≥1 commande) ; DISTINCT customer_unique_id, statuts admissibles au numérateur et dénominateur.","Cohorte première commande, mois, état","Évaluer fidélisation et cibler les actions de réachat."],
    ]
    wraps=[21,49,24,30]
    rows=[["\n".join(textwrap.wrap(v,width=wraps[c],break_long_words=False)) for c,v in enumerate(row)] for row in rows]
    tbl=ax.table(cellText=rows,colLabels=["Indicateur","Formule et périmètre","Dimensions d’analyse","Décision métier"],colWidths=[.17,.39,.20,.24],cellLoc="left",loc="upper left",bbox=[0,.01,1,.89])
    tbl.auto_set_font_size(False); tbl.set_fontsize(7.4)
    for (r,c),cell in tbl.get_celld().items():
        cell.set_edgecolor("#b7c9d6"); cell.PAD=.035
        if r==0:
            cell.set_facecolor("#164e63"); cell.get_text().set_color("white"); cell.get_text().set_weight("bold"); cell.get_text().set_fontsize(8)
        else:
            cell.set_facecolor("#f2f7fa" if r%2 else "white"); cell.get_text().set_color("#243b53"); cell.get_text().set_va("center")
    fig.savefig(PREVIEW/"page_kpi.png",dpi=110)
    pdf.savefig(fig); plt.close(fig)

def build_pdf(data):
    pdfpath=OUT/"Livrable_2_KPI_Schema_Etoile.pdf"; diag=OUT/"schema_etoile.png"
    q=data["quality"]
    m=data["metrics"]
    def fr(value, digits=0):
        if value is None: return "non calculé"
        return f"{value:,.{digits}f}".replace(",","X").replace(".",",").replace("X"," ")
    fig=make_star(diag)
    with PdfPages(pdfpath) as pdf:
        page_text(pdf,"LIVRABLE 2 | Pilotage de la marketplace Olist",[
          ("Contexte et problématique","Comment piloter conjointement la performance commerciale, la qualité des livraisons et l’expérience client d’Olist, en repérant les catégories, vendeurs et zones qui contribuent aux ventes ou concentrent les retards et avis défavorables ?"),
          ("Objectifs du tableau de bord","Suivre le volume et la valeur des commandes, distinguer le prix des articles des frais de transport, mesurer le respect des délais, et relier satisfaction et réachat à l’activité commerciale. Les résultats doivent être filtrables sans additionner des faits de granularités différentes."),
          ("Public cible","Direction générale : tendances et arbitrages. Responsable commercial : ventes, catégories, panier. Responsable logistique : durées et retards. Relation client : notes et satisfaction. Responsable marketplace : contribution des vendeurs et fidélité des acheteurs."),
          ("Périmètre de calcul","GMV admissible et commandes : statuts autres que canceled et unavailable (approved, created, invoiced, processing, shipped, delivered). GMV livré : status='delivered' uniquement. Les commandes admissibles non livrées restent dans le premier indicateur, mais pas dans les durées/taux logistiques. Les avis suivent leur périmètre propre : avis avec score valide."),
          ("Valeurs calculées et limite d’interprétation",f"Sur la base locale : GMV admissible = {fr(m['gmv_admissible_items_brl'],2)} BRL ; GMV livré = {fr(m['gmv_delivered_items_brl'],2)} BRL. GMV = valeur des articles (price), hors freight_value, qui reste distinct. Le jeu ne donne ni coûts ni marge : GMV n’est ni un revenu comptable net ni un bénéfice."),
          ("Synthèse des KPI observés",f"Commandes admissibles : {m['orders_admissible']:,}, dont {m['eligible_orders_with_items']:,} avec articles et {m['eligible_orders_without_items']:,} sans article. Panier principal (commandes avec article) : {fr(m['basket_mean_with_items_brl'],2)} BRL ; variante divisée par toutes les commandes admissibles : {fr(m['basket_mean_all_eligible_brl'],2)} BRL. Délai moyen : {fr(m['avg_delivery_days'],2)} jours ; retard : {m['late_delivered_count']:,}/{m['delivery_evaluable_count']:,} ({fr(m['late_rate_percent'],2)} %). Note : {fr(m['review_avg_score'],2)}/5 ; satisfaction : {fr(m['review_satisfaction_percent'],2)} % (scores 1–5). Réachat : {fr(m['repeat_customers']['rate_percent'],2)} %. Calculs issus des statuts admissibles pour le commerce/réachat, des commandes livrées et évaluables pour la logistique, et des avis à score valide."),
        ],10.1)
        page_kpis(pdf,data)
        # diagram page
        fig2=make_star(diag); pdf.savefig(fig2); plt.close(fig2)
        page_text(pdf,"Sources, qualité et règles de préparation",[
          ("Sources réellement présentes","Schéma raw de warehouse.duckdb : customers, orders, order_items, order_payments, order_reviews, products, sellers, geolocation, category_translation. CSV correspondants présents sous Data/. Les compteurs et types exacts sont consignés dans livrables/analyse_olist.json. L’analyse et l’export accèdent à la base en lecture seule."),
          ("Règles proposées","Clés vérifiées : order_id, (order_id, order_item_id), (order_id, payment_sequential), product_id, seller_id et customer_id. review_id n’est pas unique ; conserver toutes les lignes et les relier à la commande par order_id. review_row_key sera une clé substitut générée dans le modèle final, absente des fichiers Olist bruts. Agréger paiements/avis séparément par commande avant rapprochement aux articles."),
          ("Valeurs absentes et catégories","Conserver et quantifier les dates de livraison absentes ; exclure uniquement du dénominateur livraison. Conserver les champs optionnels manquants de products sans inventer de catégorie ; traduire avec category_translation et étiqueter « inconnue ». Une clé de géolocalisation ZIP peut avoir plusieurs coordonnées : ne pas joindre geolocation brute, qui multiplierait les lignes ; retenir un mapping documenté/déterministe si une analyse géographique fine est requise."),
          ("Commandes et cohérence","Exclure canceled et unavailable des KPI commerciaux selon le périmètre retenu, sans supprimer la source ; analyser ces statuts séparément. Pour retard, utiliser les deux dates réelle et estimée. Vérifier commandes sans article, sans paiement, durée négative et doublons de clés. Une anomalie est signalée, jamais corrigée silencieusement."),
          ("Avis et clients récurrents",f"{q['reviews'][0][0]:,} lignes d’avis, {q['reviews'][0][1]:,} review_id distincts, {q['reviews'][0][3]:,} lignes en excès, {q['review_id_repeated_groups'][0][0]:,} identifiants répétés ; doublons de ligne totalement identiques : {q['review_exact_duplicate_rows'][0][0]:,}. {q['reviews_multi'][0][0]:,} commandes ont plusieurs avis. Conserver les lignes ; PK technique de fait proposée. Réachat : {m['repeat_customers']['numerator_people']:,}/{m['repeat_customers']['denominator_people']:,} personnes = {fr(m['repeat_customers']['rate_percent'],2)} %, customer_unique_id et même périmètre de statuts."),
          ("Contrôles et résultats",f"Commandes admissibles : {m['orders_admissible']:,}, dont {m['eligible_orders_without_items']:,} sans article. Tous statuts : {q['orders_without_items'][0][0]:,} sans article et {q['orders_without_payments'][0][0]:,} sans paiement. Clés en excès : commandes {q['orders_dups'][0][0]:,}, articles {q['items_key'][0][1]:,}, paiements {q['payments_key'][0][2]:,}, seller_id {q['dimension_key_duplicates'][0][1]:,}, customer_id {q['dimension_key_duplicates'][0][2]:,}. NULL : date de livraison client {q['orders_nulls'][0][1]:,}, date transporteur {q['orders_nulls'][0][2]:,}, catégorie produit {q['products_nullcat'][0][0]:,}. Durées négatives : {m['negative_delivery_durations']:,} ; livré avant prise en charge : {q['delivery_date_controls'][0][3]:,} ; prise en charge avant achat : {q['delivery_date_controls'][0][4]:,}. Retards : {m['late_delivered_count']:,}/{m['delivery_evaluable_count']:,}. Détails par colonne dans JSON."),
          ("Limites techniques du dépôt","Les scripts existants n’ont pas été modifiés. load_data.py pointe vers data/raw alors que les CSV sont dans Data/ ; le script de chargement n’est donc pas reproductible sans correction de chemin. Le projet dbt contient un staging clients et des modèles exemple. Aucun nettoyage n’est appliqué dans warehouse.duckdb."),
        ],9.5)
    return pdfpath,diag

if __name__ == "__main__":
    data=analyze()
    (OUT/"analyse_olist.json").write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
    p,d=build_pdf(data)
    print(json.dumps({"pdf":str(p),"diagram":str(d),"analysis":str(OUT/"analyse_olist.json"),"counts":{k:v['rows'] for k,v in data['tables'].items()},"quality":data['quality']},ensure_ascii=False,indent=2,default=str))
