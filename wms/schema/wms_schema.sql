--
-- PostgreSQL database dump
--

\restrict haLta2yIse4Im5YqkJLHc4qswffU2fivyS58NHKA0AyUzY1ARxfFNlVuZ73Qrmb

-- Dumped from database version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: wms; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA wms;


--
-- Name: maj_date_maj(); Type: FUNCTION; Schema: wms; Owner: -
--

CREATE FUNCTION wms.maj_date_maj() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
   NEW.date_maj := now();
   RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: customer; Type: TABLE; Schema: wms; Owner: -
--

CREATE TABLE wms.customer (
    customer_id bigint NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    date_maj timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: customer_customer_id_seq; Type: SEQUENCE; Schema: wms; Owner: -
--

CREATE SEQUENCE wms.customer_customer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: customer_customer_id_seq; Type: SEQUENCE OWNED BY; Schema: wms; Owner: -
--

ALTER SEQUENCE wms.customer_customer_id_seq OWNED BY wms.customer.customer_id;


--
-- Name: inventory; Type: TABLE; Schema: wms; Owner: -
--

CREATE TABLE wms.inventory (
    inventory_id bigint NOT NULL,
    item_id bigint NOT NULL,
    location_id bigint NOT NULL,
    qty_on_hand numeric(18,3) DEFAULT 0 NOT NULL,
    qty_reserved numeric(18,3) DEFAULT 0 NOT NULL,
    date_maj timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_qty_nonneg CHECK (((qty_on_hand >= (0)::numeric) AND (qty_reserved >= (0)::numeric)))
);


--
-- Name: inventory_inventory_id_seq; Type: SEQUENCE; Schema: wms; Owner: -
--

CREATE SEQUENCE wms.inventory_inventory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inventory_inventory_id_seq; Type: SEQUENCE OWNED BY; Schema: wms; Owner: -
--

ALTER SEQUENCE wms.inventory_inventory_id_seq OWNED BY wms.inventory.inventory_id;


--
-- Name: item; Type: TABLE; Schema: wms; Owner: -
--

CREATE TABLE wms.item (
    item_id bigint NOT NULL,
    sku text NOT NULL,
    description text NOT NULL,
    uom text DEFAULT 'EA'::text NOT NULL,
    date_maj timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: item_item_id_seq; Type: SEQUENCE; Schema: wms; Owner: -
--

CREATE SEQUENCE wms.item_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: item_item_id_seq; Type: SEQUENCE OWNED BY; Schema: wms; Owner: -
--

ALTER SEQUENCE wms.item_item_id_seq OWNED BY wms.item.item_id;


--
-- Name: location; Type: TABLE; Schema: wms; Owner: -
--

CREATE TABLE wms.location (
    location_id bigint NOT NULL,
    warehouse_id bigint NOT NULL,
    code text NOT NULL,
    type text NOT NULL,
    date_maj timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT location_type_check CHECK ((type = ANY (ARRAY['RECEIVING'::text, 'STORAGE'::text, 'PICK'::text, 'PACK'::text, 'SHIPPING'::text])))
);


--
-- Name: location_location_id_seq; Type: SEQUENCE; Schema: wms; Owner: -
--

CREATE SEQUENCE wms.location_location_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: location_location_id_seq; Type: SEQUENCE OWNED BY; Schema: wms; Owner: -
--

ALTER SEQUENCE wms.location_location_id_seq OWNED BY wms.location.location_id;


--
-- Name: order_line; Type: TABLE; Schema: wms; Owner: -
--

CREATE TABLE wms.order_line (
    order_line_id bigint NOT NULL,
    order_id bigint NOT NULL,
    line_no integer NOT NULL,
    item_id bigint NOT NULL,
    qty_ordered numeric(18,3) NOT NULL,
    qty_picked numeric(18,3) DEFAULT 0 NOT NULL,
    date_maj timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT order_line_qty_ordered_check CHECK ((qty_ordered > (0)::numeric)),
    CONSTRAINT order_line_qty_picked_check CHECK ((qty_picked >= (0)::numeric))
);


--
-- Name: order_line_order_line_id_seq; Type: SEQUENCE; Schema: wms; Owner: -
--

CREATE SEQUENCE wms.order_line_order_line_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_line_order_line_id_seq; Type: SEQUENCE OWNED BY; Schema: wms; Owner: -
--

ALTER SEQUENCE wms.order_line_order_line_id_seq OWNED BY wms.order_line.order_line_id;


--
-- Name: orders; Type: TABLE; Schema: wms; Owner: -
--

CREATE TABLE wms.orders (
    order_id bigint NOT NULL,
    order_no text NOT NULL,
    customer_id bigint NOT NULL,
    order_date timestamp with time zone DEFAULT now() NOT NULL,
    status text DEFAULT 'CREATED'::text NOT NULL,
    date_maj timestamp with time zone DEFAULT now() NOT NULL,
    warehouse_id bigint,
    CONSTRAINT orders_status_check CHECK ((status = ANY (ARRAY['CREATED'::text, 'ALLOCATED'::text, 'PICKED'::text, 'PACKED'::text, 'SHIPPED'::text, 'CANCELLED'::text])))
);


--
-- Name: orders_order_id_seq; Type: SEQUENCE; Schema: wms; Owner: -
--

CREATE SEQUENCE wms.orders_order_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: orders_order_id_seq; Type: SEQUENCE OWNED BY; Schema: wms; Owner: -
--

ALTER SEQUENCE wms.orders_order_id_seq OWNED BY wms.orders.order_id;


--
-- Name: shipment; Type: TABLE; Schema: wms; Owner: -
--

CREATE TABLE wms.shipment (
    shipment_id bigint NOT NULL,
    order_id bigint NOT NULL,
    carrier text,
    tracking_no text,
    shipped_at timestamp with time zone,
    date_maj timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: shipment_shipment_id_seq; Type: SEQUENCE; Schema: wms; Owner: -
--

CREATE SEQUENCE wms.shipment_shipment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shipment_shipment_id_seq; Type: SEQUENCE OWNED BY; Schema: wms; Owner: -
--

ALTER SEQUENCE wms.shipment_shipment_id_seq OWNED BY wms.shipment.shipment_id;


--
-- Name: warehouse; Type: TABLE; Schema: wms; Owner: -
--

CREATE TABLE wms.warehouse (
    warehouse_id bigint NOT NULL,
    code text NOT NULL,
    name text NOT NULL,
    date_maj timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: warehouse_warehouse_id_seq; Type: SEQUENCE; Schema: wms; Owner: -
--

CREATE SEQUENCE wms.warehouse_warehouse_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: warehouse_warehouse_id_seq; Type: SEQUENCE OWNED BY; Schema: wms; Owner: -
--

ALTER SEQUENCE wms.warehouse_warehouse_id_seq OWNED BY wms.warehouse.warehouse_id;


--
-- Name: customer customer_id; Type: DEFAULT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.customer ALTER COLUMN customer_id SET DEFAULT nextval('wms.customer_customer_id_seq'::regclass);


--
-- Name: inventory inventory_id; Type: DEFAULT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.inventory ALTER COLUMN inventory_id SET DEFAULT nextval('wms.inventory_inventory_id_seq'::regclass);


--
-- Name: item item_id; Type: DEFAULT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.item ALTER COLUMN item_id SET DEFAULT nextval('wms.item_item_id_seq'::regclass);


--
-- Name: location location_id; Type: DEFAULT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.location ALTER COLUMN location_id SET DEFAULT nextval('wms.location_location_id_seq'::regclass);


--
-- Name: order_line order_line_id; Type: DEFAULT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.order_line ALTER COLUMN order_line_id SET DEFAULT nextval('wms.order_line_order_line_id_seq'::regclass);


--
-- Name: orders order_id; Type: DEFAULT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.orders ALTER COLUMN order_id SET DEFAULT nextval('wms.orders_order_id_seq'::regclass);


--
-- Name: shipment shipment_id; Type: DEFAULT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.shipment ALTER COLUMN shipment_id SET DEFAULT nextval('wms.shipment_shipment_id_seq'::regclass);


--
-- Name: warehouse warehouse_id; Type: DEFAULT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.warehouse ALTER COLUMN warehouse_id SET DEFAULT nextval('wms.warehouse_warehouse_id_seq'::regclass);


--
-- Name: customer customer_code_key; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.customer
    ADD CONSTRAINT customer_code_key UNIQUE (code);


--
-- Name: customer customer_pkey; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.customer
    ADD CONSTRAINT customer_pkey PRIMARY KEY (customer_id);


--
-- Name: inventory inventory_item_id_location_id_key; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.inventory
    ADD CONSTRAINT inventory_item_id_location_id_key UNIQUE (item_id, location_id);


--
-- Name: inventory inventory_pkey; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.inventory
    ADD CONSTRAINT inventory_pkey PRIMARY KEY (inventory_id);


--
-- Name: item item_pkey; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.item
    ADD CONSTRAINT item_pkey PRIMARY KEY (item_id);


--
-- Name: item item_sku_key; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.item
    ADD CONSTRAINT item_sku_key UNIQUE (sku);


--
-- Name: location location_pkey; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.location
    ADD CONSTRAINT location_pkey PRIMARY KEY (location_id);


--
-- Name: location location_warehouse_id_code_key; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.location
    ADD CONSTRAINT location_warehouse_id_code_key UNIQUE (warehouse_id, code);


--
-- Name: order_line order_line_order_id_line_no_key; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.order_line
    ADD CONSTRAINT order_line_order_id_line_no_key UNIQUE (order_id, line_no);


--
-- Name: order_line order_line_pkey; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.order_line
    ADD CONSTRAINT order_line_pkey PRIMARY KEY (order_line_id);


--
-- Name: orders orders_order_no_key; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.orders
    ADD CONSTRAINT orders_order_no_key UNIQUE (order_no);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (order_id);


--
-- Name: shipment shipment_pkey; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.shipment
    ADD CONSTRAINT shipment_pkey PRIMARY KEY (shipment_id);


--
-- Name: warehouse warehouse_code_key; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.warehouse
    ADD CONSTRAINT warehouse_code_key UNIQUE (code);


--
-- Name: warehouse warehouse_pkey; Type: CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.warehouse
    ADD CONSTRAINT warehouse_pkey PRIMARY KEY (warehouse_id);


--
-- Name: ix_customer_date_maj; Type: INDEX; Schema: wms; Owner: -
--

CREATE INDEX ix_customer_date_maj ON wms.customer USING btree (date_maj);


--
-- Name: ix_inventory_date_maj; Type: INDEX; Schema: wms; Owner: -
--

CREATE INDEX ix_inventory_date_maj ON wms.inventory USING btree (date_maj);


--
-- Name: ix_item_date_maj; Type: INDEX; Schema: wms; Owner: -
--

CREATE INDEX ix_item_date_maj ON wms.item USING btree (date_maj);


--
-- Name: ix_location_date_maj; Type: INDEX; Schema: wms; Owner: -
--

CREATE INDEX ix_location_date_maj ON wms.location USING btree (date_maj);


--
-- Name: ix_order_line_date_maj; Type: INDEX; Schema: wms; Owner: -
--

CREATE INDEX ix_order_line_date_maj ON wms.order_line USING btree (date_maj);


--
-- Name: ix_orders_date_maj; Type: INDEX; Schema: wms; Owner: -
--

CREATE INDEX ix_orders_date_maj ON wms.orders USING btree (date_maj);


--
-- Name: ix_orders_warehouse_id; Type: INDEX; Schema: wms; Owner: -
--

CREATE INDEX ix_orders_warehouse_id ON wms.orders USING btree (warehouse_id);


--
-- Name: ix_shipment_date_maj; Type: INDEX; Schema: wms; Owner: -
--

CREATE INDEX ix_shipment_date_maj ON wms.shipment USING btree (date_maj);


--
-- Name: ix_warehouse_date_maj; Type: INDEX; Schema: wms; Owner: -
--

CREATE INDEX ix_warehouse_date_maj ON wms.warehouse USING btree (date_maj);


--
-- Name: customer trg_customer_date_maj; Type: TRIGGER; Schema: wms; Owner: -
--

CREATE TRIGGER trg_customer_date_maj BEFORE UPDATE ON wms.customer FOR EACH ROW EXECUTE FUNCTION wms.maj_date_maj();


--
-- Name: inventory trg_inventory_date_maj; Type: TRIGGER; Schema: wms; Owner: -
--

CREATE TRIGGER trg_inventory_date_maj BEFORE UPDATE ON wms.inventory FOR EACH ROW EXECUTE FUNCTION wms.maj_date_maj();


--
-- Name: item trg_item_date_maj; Type: TRIGGER; Schema: wms; Owner: -
--

CREATE TRIGGER trg_item_date_maj BEFORE UPDATE ON wms.item FOR EACH ROW EXECUTE FUNCTION wms.maj_date_maj();


--
-- Name: location trg_location_date_maj; Type: TRIGGER; Schema: wms; Owner: -
--

CREATE TRIGGER trg_location_date_maj BEFORE UPDATE ON wms.location FOR EACH ROW EXECUTE FUNCTION wms.maj_date_maj();


--
-- Name: order_line trg_order_line_date_maj; Type: TRIGGER; Schema: wms; Owner: -
--

CREATE TRIGGER trg_order_line_date_maj BEFORE UPDATE ON wms.order_line FOR EACH ROW EXECUTE FUNCTION wms.maj_date_maj();


--
-- Name: orders trg_orders_date_maj; Type: TRIGGER; Schema: wms; Owner: -
--

CREATE TRIGGER trg_orders_date_maj BEFORE UPDATE ON wms.orders FOR EACH ROW EXECUTE FUNCTION wms.maj_date_maj();


--
-- Name: shipment trg_shipment_date_maj; Type: TRIGGER; Schema: wms; Owner: -
--

CREATE TRIGGER trg_shipment_date_maj BEFORE UPDATE ON wms.shipment FOR EACH ROW EXECUTE FUNCTION wms.maj_date_maj();


--
-- Name: warehouse trg_warehouse_date_maj; Type: TRIGGER; Schema: wms; Owner: -
--

CREATE TRIGGER trg_warehouse_date_maj BEFORE UPDATE ON wms.warehouse FOR EACH ROW EXECUTE FUNCTION wms.maj_date_maj();


--
-- Name: inventory inventory_item_id_fkey; Type: FK CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.inventory
    ADD CONSTRAINT inventory_item_id_fkey FOREIGN KEY (item_id) REFERENCES wms.item(item_id) ON DELETE RESTRICT;


--
-- Name: inventory inventory_location_id_fkey; Type: FK CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.inventory
    ADD CONSTRAINT inventory_location_id_fkey FOREIGN KEY (location_id) REFERENCES wms.location(location_id) ON DELETE RESTRICT;


--
-- Name: location location_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.location
    ADD CONSTRAINT location_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES wms.warehouse(warehouse_id) ON DELETE CASCADE;


--
-- Name: order_line order_line_item_id_fkey; Type: FK CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.order_line
    ADD CONSTRAINT order_line_item_id_fkey FOREIGN KEY (item_id) REFERENCES wms.item(item_id) ON DELETE RESTRICT;


--
-- Name: order_line order_line_order_id_fkey; Type: FK CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.order_line
    ADD CONSTRAINT order_line_order_id_fkey FOREIGN KEY (order_id) REFERENCES wms.orders(order_id) ON DELETE CASCADE;


--
-- Name: orders orders_customer_id_fkey; Type: FK CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.orders
    ADD CONSTRAINT orders_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES wms.customer(customer_id) ON DELETE RESTRICT;


--
-- Name: orders orders_warehouse_id_fkey; Type: FK CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.orders
    ADD CONSTRAINT orders_warehouse_id_fkey FOREIGN KEY (warehouse_id) REFERENCES wms.warehouse(warehouse_id);


--
-- Name: shipment shipment_order_id_fkey; Type: FK CONSTRAINT; Schema: wms; Owner: -
--

ALTER TABLE ONLY wms.shipment
    ADD CONSTRAINT shipment_order_id_fkey FOREIGN KEY (order_id) REFERENCES wms.orders(order_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict haLta2yIse4Im5YqkJLHc4qswffU2fivyS58NHKA0AyUzY1ARxfFNlVuZ73Qrmb

