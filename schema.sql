-- Database schema for Shopline scraper

-- Main SKU information table
CREATE TABLE IF NOT EXISTS api_bc_skuinfo (
    id SERIAL PRIMARY KEY,
    product_id VARCHAR(100) NOT NULL,
    listing_id VARCHAR(100),
    website_name VARCHAR(500),
    is_visible VARCHAR(1),
    date_created VARCHAR(50),
    sku VARCHAR(200) NOT NULL,
    price DECIMAL(10, 2),
    sale_price DECIMAL(10, 2),
    inventory_level INTEGER DEFAULT 0,
    image_url TEXT,
    custom_url VARCHAR(500),
    handle VARCHAR(200),
    inventory_item_id VARCHAR(100),
    productimg_url TEXT,
    variant_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- History records table
CREATE TABLE IF NOT EXISTS hisrecord_bcsku (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(100),
    sku VARCHAR(200) NOT NULL,
    price DECIMAL(10, 2),
    sale_price DECIMAL(10, 2),
    inventory_level INTEGER DEFAULT 0,
    is_visible VARCHAR(1),
    recorddate DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_skuinfo_sku ON api_bc_skuinfo(sku);
CREATE INDEX IF NOT EXISTS idx_skuinfo_product_id ON api_bc_skuinfo(product_id);
CREATE INDEX IF NOT EXISTS idx_skuinfo_listing_id ON api_bc_skuinfo(listing_id);
CREATE INDEX IF NOT EXISTS idx_skuinfo_variant_id ON api_bc_skuinfo(variant_id);

CREATE INDEX IF NOT EXISTS idx_history_sku ON hisrecord_bcsku(sku);
CREATE INDEX IF NOT EXISTS idx_history_date ON hisrecord_bcsku(recorddate);
CREATE INDEX IF NOT EXISTS idx_history_listing_id ON hisrecord_bcsku(listing_id);

-- Comments
COMMENT ON TABLE api_bc_skuinfo IS 'Shopline product SKU information';
COMMENT ON TABLE hisrecord_bcsku IS 'Historical records of SKU data';
