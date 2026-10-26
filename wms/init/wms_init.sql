\set ON_ERROR_STOP on

-- Cible : base "postgres"
-- Crée un schéma dédié et des tables WMS d'exemple, puis charge des commandes depuis un bloc texte.

CREATE SCHEMA IF NOT EXISTS wms;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Nettoyage optionnel (décommenter si tu veux repartir de zéro)
-- DROP SCHEMA wms CASCADE;
-- CREATE SCHEMA wms;

-- 1) Tables
CREATE TABLE IF NOT EXISTS wms.warehouse (
  warehouse_id  bigserial PRIMARY KEY,
  code          text NOT NULL UNIQUE,
  name          text NOT NULL
);

CREATE TABLE IF NOT EXISTS wms.location (
  location_id   bigserial PRIMARY KEY,
  warehouse_id  bigint NOT NULL REFERENCES wms.warehouse(warehouse_id) ON DELETE CASCADE,
  code          text NOT NULL,
  type          text NOT NULL CHECK (type IN ('RECEIVING','STORAGE','PICK','PACK','SHIPPING')),
  UNIQUE (warehouse_id, code)
);

CREATE TABLE IF NOT EXISTS wms.item (
  item_id       bigserial PRIMARY KEY,
  sku           text NOT NULL UNIQUE,
  description   text NOT NULL,
  uom           text NOT NULL DEFAULT 'EA'
);

CREATE TABLE IF NOT EXISTS wms.customer (
  customer_id   bigserial PRIMARY KEY,
  code          text NOT NULL UNIQUE,
  name          text NOT NULL
);

CREATE TABLE IF NOT EXISTS wms.inventory (
  inventory_id  bigserial PRIMARY KEY,
  item_id       bigint NOT NULL REFERENCES wms.item(item_id) ON DELETE RESTRICT,
  location_id   bigint NOT NULL REFERENCES wms.location(location_id) ON DELETE RESTRICT,
  qty_on_hand   numeric(18,3) NOT NULL DEFAULT 0,
  qty_reserved  numeric(18,3) NOT NULL DEFAULT 0,
  CONSTRAINT chk_qty_nonneg CHECK (qty_on_hand >= 0 AND qty_reserved >= 0),
  UNIQUE(item_id, location_id)
);

-- order_no en TEXT pour accepter "1..5" et "ORDxxxxxxx"
CREATE TABLE IF NOT EXISTS wms.orders (
  order_id      bigserial PRIMARY KEY,
  order_no      text NOT NULL UNIQUE,
  customer_id   bigint NOT NULL REFERENCES wms.customer(customer_id) ON DELETE RESTRICT,
  order_date    timestamptz NOT NULL DEFAULT now(),
  status        text NOT NULL DEFAULT 'CREATED'
               CHECK (status IN ('CREATED','ALLOCATED','PICKED','PACKED','SHIPPED','CANCELLED'))
);

CREATE TABLE IF NOT EXISTS wms.order_line (
  order_line_id bigserial PRIMARY KEY,
  order_id      bigint NOT NULL REFERENCES wms.orders(order_id) ON DELETE CASCADE,
  line_no       int NOT NULL,
  item_id       bigint NOT NULL REFERENCES wms.item(item_id) ON DELETE RESTRICT,
  qty_ordered   numeric(18,3) NOT NULL CHECK (qty_ordered > 0),
  qty_picked    numeric(18,3) NOT NULL DEFAULT 0 CHECK (qty_picked >= 0),
  UNIQUE(order_id, line_no)
);

CREATE TABLE IF NOT EXISTS wms.shipment (
  shipment_id   bigserial PRIMARY KEY,
  order_id      bigint NOT NULL REFERENCES wms.orders(order_id) ON DELETE CASCADE,
  carrier       text,
  tracking_no   text,
  shipped_at    timestamptz
);

-- 2) Données de référence
INSERT INTO wms.warehouse(code, name)
VALUES ('WH1', 'Entrepôt principal')
ON CONFLICT (code) DO NOTHING;

INSERT INTO wms.location(warehouse_id, code, type)
SELECT w.warehouse_id, v.code, v.type
FROM wms.warehouse w
CROSS JOIN (VALUES
  ('RCV-01','RECEIVING'),
  ('STO-01','STORAGE'),
  ('STO-02','STORAGE'),
  ('PICK-01','PICK'),
  ('PACK-01','PACK'),
  ('SHP-01','SHIPPING')
) AS v(code, type)
WHERE w.code = 'WH1'
ON CONFLICT (warehouse_id, code) DO NOTHING;

INSERT INTO wms.item(sku, description, uom)
VALUES
  ('SKU-0001','Gants nitrile - taille M','EA'),
  ('SKU-0002','Carton 40x30x20','EA'),
  ('SKU-0003','Ruban adhésif 50mm','EA'),
  ('SKU-0004','T-shirt coton - noir - L','EA'),
  ('SKU-0005','Bouteille inox 1L','EA')
ON CONFLICT (sku) DO NOTHING;

INSERT INTO wms.customer(code, name)
VALUES ('CUST-001', 'Client Démo')
ON CONFLICT (code) DO NOTHING;

INSERT INTO wms.inventory(item_id, location_id, qty_on_hand, qty_reserved)
SELECT i.item_id, l.location_id,
       CASE i.sku
         WHEN 'SKU-0001' THEN 500
         WHEN 'SKU-0002' THEN 200
         WHEN 'SKU-0003' THEN 300
         WHEN 'SKU-0004' THEN 150
         WHEN 'SKU-0005' THEN 120
         ELSE 0
       END::numeric(18,3),
       0
FROM wms.item i
JOIN wms.location l ON l.code IN ('STO-01','STO-02')
ON CONFLICT (item_id, location_id) DO NOTHING;

-- 3) Charger les numéros de commande depuis un bloc texte
DROP TABLE IF EXISTS wms._order_no_raw;
CREATE TABLE wms._order_no_raw(raw text NOT NULL);

-- IMPORTANT :
-- Colle ici TOUTE ta liste (tu peux remplacer le bloc ci-dessous par ta liste complète).
INSERT INTO wms._order_no_raw(raw) VALUES ($$
1
2
3
4
5
ORD3950771
ORD6003194
ORD8644221
ORD4574632
ORD2041973
-- ... (garde tout ce que tu as collé, puis colle la suite)
ORD4294412
$$);

WITH tokens AS (
  SELECT NULLIF(btrim(x), '') AS order_no
  FROM wms._order_no_raw r
  CROSS JOIN LATERAL regexp_split_to_table(r.raw, E'[\\r\\n]+') AS x
),
dedup AS (
  SELECT DISTINCT order_no
  FROM tokens
  WHERE order_no IS NOT NULL
)
INSERT INTO wms.orders(order_no, customer_id, order_date, status)
SELECT d.order_no,
       c.customer_id,
       now() - ((random() * 30)::int || ' days')::interval,
       'CREATED'
FROM dedup d
CROSS JOIN (SELECT customer_id FROM wms.customer WHERE code = 'CUST-001') c
ON CONFLICT (order_no) DO NOTHING;

-- 4) Générer 2 lignes par commande
WITH o AS (
  SELECT order_id
  FROM wms.orders
),
ln AS (
  SELECT o.order_id, gs AS line_no
  FROM o
  CROSS JOIN generate_series(1,2) gs
),
items AS (
  SELECT item_id, row_number() OVER (ORDER BY sku) AS rn
  FROM wms.item
)
INSERT INTO wms.order_line(order_id, line_no, item_id, qty_ordered, qty_picked)
SELECT ln.order_id,
       ln.line_no,
       i.item_id,
       (1 + (random() * 5)::int)::numeric(18,3),
       0
FROM ln
JOIN items i
  ON i.rn = (1 + ((abs(hashtextextended(ln.order_id::text || '-' || ln.line_no::text, 0)) % 5)))::int
ON CONFLICT (order_id, line_no) DO NOTHING;

-- 5) Vérifs
SELECT count(*) AS nb_orders FROM wms.orders;

SELECT order_no, status, order_date
FROM wms.orders
ORDER BY order_no
LIMIT 20;