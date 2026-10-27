# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "f6523eec-e450-401b-a672-cebe8d1ef2af",
# META       "default_lakehouse_name": "AmazingZoneLK",
# META       "default_lakehouse_workspace_id": "0875373d-96cd-4d0e-b4e7-5fc5cd327cb8",
# META       "known_lakehouses": [
# META         {
# META           "id": "f6523eec-e450-401b-a672-cebe8d1ef2af"
# META         }
# META       ]
# META     }
# META   }
# META }

# MARKDOWN ********************

# # Variante : couche Silver en vues matérialisées (Materialized Lake Views)
# # Amazing Zone construit ses couches Silver et Gold avec dbt dans le Warehouse AmazingZoneWH (job
# « Silver et Gold - Nettoyage et modèle en étoile »). Ce notebook documente et déploie la **variante** de la couche Silver dans le Lakehouse, en vues
# matérialisées déclaratives, dans un schéma `silver_mlv` distinct pour ne pas la confondre avec la Silver du
# Warehouse. Il n'est pas appelé par l'orchestration.
# # - Sources : Bronze du Lakehouse (raccourcis `ecommerce` vers la base mirrorée, tables `wms`, `meteo`, `referentiels`).
# - Le flux de modifications (Change Data Feed) est activé sur les tables sources du Lakehouse ; il ne l'est pas sur
#   les tables mirrorées (capacité étendue du mirroring, facturée) : les vues qui en dépendent sont recalculées.
# - Les sources du WMS sont fusionnées (mises à jour) par le Copy Job : sans clé déclarée, le rafraîchissement
#   optimal retomberait sur un recalcul complet. Chaque vue déclare donc une clé avec `REFRESH_HINT` (préversion).
# - Un LEFT JOIN n'est incrémental que si sa table de droite n'a pas changé : `commande_logistique` reste
#   généralement recalculée en entier.

# CELL ********************

# MAGIC %%sql
# MAGIC SET spark.materialized.lake.views.dv.auto.create.enabled = true

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC CREATE SCHEMA IF NOT EXISTS silver_mlv

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC ALTER TABLE wms.orders SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC ALTER TABLE wms.order_line SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC ALTER TABLE wms.shipment SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC ALTER TABLE wms.inventory SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC ALTER TABLE wms.item SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC ALTER TABLE wms.location SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC ALTER TABLE wms.warehouse SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC ALTER TABLE meteo.weather_forecast SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC ALTER TABLE referentiels.geographie SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC CREATE OR REPLACE MATERIALIZED LAKE VIEW silver_mlv.entrepot
# MAGIC (
# MAGIC     REFRESH_HINT cle_entrepot UNIQUE (code_entrepot)
# MAGIC )
# MAGIC COMMENT "Entrepôts d'Amazing Zone (WMS), avec les coordonnées utilisées pour la météo"
# MAGIC AS
# MAGIC SELECT w.code                                        AS code_entrepot,
# MAGIC        w.name                                        AS entrepot,
# MAGIC        regexp_extract(w.name, '\\(([^)]+)\\)', 1)    AS ville,
# MAGIC        m.latitude,
# MAGIC        m.longitude
# MAGIC FROM wms.warehouse AS w
# MAGIC LEFT JOIN (SELECT site, MAX(latitude) AS latitude, MAX(longitude) AS longitude
# MAGIC            FROM meteo.weather_forecast GROUP BY site) AS m
# MAGIC        ON m.site = w.code

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC CREATE OR REPLACE MATERIALIZED LAKE VIEW silver_mlv.commande_logistique
# MAGIC (
# MAGIC     CONSTRAINT numero_commande_renseigne CHECK (numero_commande IS NOT NULL) ON MISMATCH DROP
# MAGIC )
# MAGIC (
# MAGIC     REFRESH_HINT cle_commande UNIQUE (commande_wms_id)
# MAGIC )
# MAGIC COMMENT "Commandes logistiques du WMS : entrepôt de préparation, statut, expédition (une ligne par commande)"
# MAGIC AS
# MAGIC WITH lignes AS (
# MAGIC     SELECT order_id, COUNT(*) AS nb_lignes, SUM(qty_ordered) AS nb_articles
# MAGIC     FROM wms.order_line
# MAGIC     GROUP BY order_id
# MAGIC ),
# MAGIC expeditions AS (
# MAGIC     SELECT order_id, MIN(shipped_at) AS date_expedition, MAX(carrier) AS transporteur,
# MAGIC            MAX(tracking_no) AS numero_suivi
# MAGIC     FROM wms.shipment
# MAGIC     GROUP BY order_id
# MAGIC )
# MAGIC SELECT o.order_id                                  AS commande_wms_id,
# MAGIC        o.order_no                                  AS numero_commande,
# MAGIC        w.code                                      AS code_entrepot,
# MAGIC        CASE o.status WHEN 'CREATED'   THEN 'Créée'    WHEN 'ALLOCATED' THEN 'Allouée'
# MAGIC                      WHEN 'PICKED'    THEN 'Prélevée' WHEN 'PACKED'    THEN 'Emballée'
# MAGIC                      WHEN 'SHIPPED'   THEN 'Expédiée' WHEN 'CANCELLED' THEN 'Annulée'
# MAGIC                      ELSE o.status END             AS statut_logistique,
# MAGIC        o.order_date                                AS date_prise_en_charge,
# MAGIC        e.date_expedition,
# MAGIC        e.transporteur,
# MAGIC        e.numero_suivi,
# MAGIC        CAST(l.nb_lignes AS INT)                    AS nb_lignes,
# MAGIC        CAST(l.nb_articles AS INT)                  AS nb_articles
# MAGIC FROM wms.orders AS o
# MAGIC LEFT JOIN wms.warehouse AS w ON w.warehouse_id = o.warehouse_id
# MAGIC LEFT JOIN lignes AS l        ON l.order_id = o.order_id
# MAGIC LEFT JOIN expeditions AS e   ON e.order_id = o.order_id

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC CREATE OR REPLACE MATERIALIZED LAKE VIEW silver_mlv.stock
# MAGIC (
# MAGIC     CONSTRAINT stock_positif CHECK (quantite_stock >= 0) ON MISMATCH DROP
# MAGIC )
# MAGIC (
# MAGIC     REFRESH_HINT cle_stock UNIQUE (sku, code_entrepot)
# MAGIC )
# MAGIC COMMENT "Stock courant du WMS par article et par entrepôt"
# MAGIC AS
# MAGIC SELECT i.sku,
# MAGIC        w.code                    AS code_entrepot,
# MAGIC        SUM(inv.qty_on_hand)      AS quantite_stock,
# MAGIC        SUM(inv.qty_reserved)     AS quantite_reservee,
# MAGIC        MAX(inv.date_maj)         AS date_maj
# MAGIC FROM wms.inventory AS inv
# MAGIC INNER JOIN wms.item AS i      ON i.item_id = inv.item_id
# MAGIC INNER JOIN wms.location AS l  ON l.location_id = inv.location_id
# MAGIC INNER JOIN wms.warehouse AS w ON w.warehouse_id = l.warehouse_id
# MAGIC GROUP BY i.sku, w.code

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC CREATE OR REPLACE MATERIALIZED LAKE VIEW silver_mlv.meteo_jour
# MAGIC (
# MAGIC     REFRESH_HINT cle_meteo UNIQUE (code_entrepot, `date`)
# MAGIC )
# MAGIC COMMENT "Météo quotidienne par entrepôt (valeurs consolidées et prévisions Open-Meteo), avec un indicateur d'intempérie"
# MAGIC AS
# MAGIC SELECT site                                  AS code_entrepot,
# MAGIC        site_nom                              AS entrepot,
# MAGIC        `date`,
# MAGIC        temperature_2m_max                    AS temperature_max,
# MAGIC        temperature_2m_min                    AS temperature_min,
# MAGIC        precipitation_sum                     AS precipitations_mm,
# MAGIC        snowfall_sum                          AS neige_cm,
# MAGIC        wind_gusts_10m_max                    AS rafales_max_kmh,
# MAGIC        CAST(weather_code AS INT)             AS code_meteo,
# MAGIC        CASE WHEN precipitation_sum >= 10 OR snowfall_sum > 0 OR wind_gusts_10m_max >= 70
# MAGIC             THEN true ELSE false END         AS est_jour_intemperie
# MAGIC FROM meteo.weather_forecast

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC CREATE OR REPLACE MATERIALIZED LAKE VIEW silver_mlv.client
# MAGIC (
# MAGIC     CONSTRAINT email_valide CHECK (email LIKE '%_@_%') ON MISMATCH DROP
# MAGIC )
# MAGIC (
# MAGIC     REFRESH_HINT cle_client UNIQUE (client_id)
# MAGIC )
# MAGIC COMMENT "Clients du site e-commerce, géographie rapprochée du référentiel par le code postal"
# MAGIC AS
# MAGIC WITH clients AS (
# MAGIC     SELECT c.Id                                  AS client_id,
# MAGIC            lower(trim(c.Email))                  AS email,
# MAGIC            c.FirstName                           AS prenom,
# MAGIC            c.LastName                            AS nom,
# MAGIC            CASE c.Gender WHEN 'M' THEN 'Homme' WHEN 'F' THEN 'Femme' END AS genre,
# MAGIC            c.ZipPostalCode                       AS code_postal,
# MAGIC            c.City                                AS ville,
# MAGIC            CASE WHEN c.ZipPostalCode LIKE '97%' THEN substr(c.ZipPostalCode, 1, 3)
# MAGIC                 WHEN c.ZipPostalCode LIKE '20%' THEN CASE WHEN c.ZipPostalCode < '20200' THEN '2A' ELSE '2B' END
# MAGIC                 ELSE substr(c.ZipPostalCode, 1, 2) END AS code_departement,
# MAGIC            CAST(c.CreatedOnUtc AS DATE)          AS date_inscription
# MAGIC     FROM ecommerce.customer AS c
# MAGIC     WHERE c.Deleted = false AND c.IsSystemAccount = false AND c.Email IS NOT NULL
# MAGIC )
# MAGIC SELECT c.client_id, c.email, c.prenom, c.nom, c.genre, c.code_postal, c.ville,
# MAGIC        g.code_departement, g.departement, g.region, c.date_inscription
# MAGIC FROM clients AS c
# MAGIC LEFT JOIN referentiels.geographie AS g ON g.code_departement = c.code_departement

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC CREATE OR REPLACE MATERIALIZED LAKE VIEW silver_mlv.produit
# MAGIC (
# MAGIC     REFRESH_HINT cle_produit UNIQUE (produit_id)
# MAGIC )
# MAGIC COMMENT "Catalogue du site e-commerce : produit, catégorie principale, prix catalogue et coût d'achat"
# MAGIC AS
# MAGIC WITH categorie_principale AS (
# MAGIC     SELECT ProductId, MIN(CategoryId) AS CategoryId
# MAGIC     FROM ecommerce.product_category_mapping
# MAGIC     GROUP BY ProductId
# MAGIC )
# MAGIC SELECT p.Id                                    AS produit_id,
# MAGIC        p.Sku                                   AS sku,
# MAGIC        p.Name                                  AS produit,
# MAGIC        coalesce(parent.Name, cat.Name)         AS univers,
# MAGIC        cat.Name                                AS categorie,
# MAGIC        CAST(p.Price AS DECIMAL(18, 2))         AS prix_vente,
# MAGIC        CAST(p.ProductCost AS DECIMAL(18, 2))   AS cout_achat,
# MAGIC        p.Published                             AS publie
# MAGIC FROM ecommerce.product AS p
# MAGIC LEFT JOIN categorie_principale AS m ON m.ProductId = p.Id
# MAGIC LEFT JOIN ecommerce.category AS cat ON cat.Id = m.CategoryId
# MAGIC LEFT JOIN ecommerce.category AS parent ON parent.Id = cat.ParentCategoryId AND cat.ParentCategoryId > 0
# MAGIC WHERE p.Deleted = false

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC CREATE OR REPLACE MATERIALIZED LAKE VIEW silver_mlv.commande_ligne
# MAGIC (
# MAGIC     CONSTRAINT quantite_positive CHECK (quantite > 0) ON MISMATCH DROP
# MAGIC )
# MAGIC (
# MAGIC     REFRESH_HINT cle_ligne UNIQUE (ligne_id)
# MAGIC )
# MAGIC COMMENT "Lignes de commande du site e-commerce, avec les statuts de la commande en clair"
# MAGIC AS
# MAGIC SELECT oi.Id                                              AS ligne_id,
# MAGIC        o.Id                                               AS commande_id,
# MAGIC        o.CustomOrderNumber                                AS numero_commande,
# MAGIC        o.CustomerId                                       AS client_id,
# MAGIC        oi.ProductId                                       AS produit_id,
# MAGIC        o.CreatedOnUtc                                     AS date_commande,
# MAGIC        o.PaidDateUtc                                      AS date_paiement,
# MAGIC        CASE o.OrderStatusId WHEN 10 THEN 'En attente' WHEN 20 THEN 'En cours'
# MAGIC                             WHEN 30 THEN 'Terminée'   WHEN 40 THEN 'Annulée' END   AS statut_commande,
# MAGIC        CASE o.ShippingMethod WHEN 'Ground' THEN 'Standard' WHEN 'Next Day Air' THEN 'Express'
# MAGIC                              WHEN 'Pickup in store' THEN 'Retrait' ELSE o.ShippingMethod END AS mode_livraison,
# MAGIC        oi.Quantity                                        AS quantite,
# MAGIC        CAST(oi.UnitPriceExclTax AS DECIMAL(18, 2))        AS prix_unitaire_ht,
# MAGIC        CAST(oi.PriceExclTax AS DECIMAL(18, 2))            AS montant_ht,
# MAGIC        CAST(oi.OriginalProductCost * oi.Quantity AS DECIMAL(18, 2)) AS cout_achat
# MAGIC FROM ecommerce.orderitem AS oi
# MAGIC INNER JOIN ecommerce.`order` AS o ON o.Id = oi.OrderId
# MAGIC WHERE o.Deleted = false

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }
