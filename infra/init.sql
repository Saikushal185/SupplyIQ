CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    unit_cost NUMERIC(10,2),
    reorder_point INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS regions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50),
    timezone VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS inventory_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    region_id UUID REFERENCES regions(id),
    quantity INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    UNIQUE (product_id, region_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS daily_sales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    region_id UUID REFERENCES regions(id),
    sale_date DATE NOT NULL,
    units_sold INTEGER NOT NULL,
    revenue NUMERIC(12,2),
    weather_temp NUMERIC(5,2),
    traffic_index NUMERIC(4,2)
);

CREATE TABLE IF NOT EXISTS supplier_shipments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    supplier_name VARCHAR(200),
    expected_date DATE,
    actual_date DATE,
    quantity INTEGER,
    status VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS forecast_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_at TIMESTAMP DEFAULT NOW(),
    product_id UUID REFERENCES products(id),
    region_id UUID REFERENCES regions(id),
    forecast_json JSONB,
    shap_json JSONB
);

CREATE INDEX IF NOT EXISTS ix_daily_sales_product_id_sale_date ON daily_sales (product_id, sale_date);
CREATE INDEX IF NOT EXISTS ix_inventory_snapshots_product_id_snapshot_date ON inventory_snapshots (product_id, snapshot_date);
CREATE INDEX IF NOT EXISTS ix_forecast_runs_product_id_run_at_desc ON forecast_runs (product_id, run_at DESC);
