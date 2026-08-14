CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DROP TABLE IF EXISTS offer_clicks CASCADE;
DROP TABLE IF EXISTS offers CASCADE;
DROP TABLE IF EXISTS price_history CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS stores CASCADE;

CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id),
    external_id VARCHAR(255),
    title VARCHAR(255) NOT NULL,
    image_url TEXT,
    product_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_store_external UNIQUE(store_id, external_id)
);

CREATE TABLE price_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    price NUMERIC(10,2) NOT NULL,
    source VARCHAR(50),
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id),
    store_id UUID REFERENCES stores(id),
    submitted_by UUID,
    source VARCHAR(50),
    title_override VARCHAR(255),
    affiliate_url TEXT,
    coupon_code VARCHAR(100),
    price_current NUMERIC(10,2) NOT NULL,
    price_original NUMERIC(10,2),
    discount_pct INT,
    status VARCHAR(50) DEFAULT 'pending',
    moderated_by UUID,
    moderated_at TIMESTAMP,
    rejection_reason TEXT,
    votes_up INT DEFAULT 0,
    votes_down INT DEFAULT 0,
    clicks INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE offer_clicks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id UUID REFERENCES offers(id),
    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DO $$
DECLARE
    v_store_id UUID := gen_random_uuid();
    v_product_id UUID := gen_random_uuid();
BEGIN
    INSERT INTO stores (id, name, slug) VALUES (v_store_id, 'Loja Exemplo', 'loja-exemplo');

    INSERT INTO products (id, store_id, external_id, title, image_url, product_url)
    VALUES (v_product_id, v_store_id, 'ext-s24', 'Smartphone Galaxy S24', 'https://loja.exemplo.com/s24.jpg', 'https://loja.exemplo.com/s24');

    INSERT INTO price_history (product_id, price, source) VALUES (v_product_id, 3500.00, 'initial_import');

    INSERT INTO offers (product_id, store_id, affiliate_url, price_current, price_original, discount_pct, status)
    VALUES (v_product_id, v_store_id, 'https://loja.exemplo.com/s24?ref=afiliado', 3500.00, 4500.00, 22, 'approved');

    INSERT INTO offers (product_id, store_id, affiliate_url, price_current, price_original, discount_pct, status)
    VALUES (v_product_id, v_store_id, 'https://loja.exemplo.com/s24?ref=afiliado', 3200.00, 4500.00, 28, 'pending');
END $$;
