CREATE TABLE IF NOT EXISTS advertisements (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    image_url TEXT NOT NULL,
    zone TEXT NOT NULL,
    CONSTRAINT advertisements_name_zone_uniq UNIQUE (name, zone)
);

INSERT INTO advertisements (name, image_url, zone) VALUES
    ('Nike Air Max', '/static/ads/airmax.png', 'glassfloor'),
    ('Adidas Predator', '/static/ads/predator.png', 'surrounding'),
    ('Coca Cola', '/static/ads/cocacola.png', 'megatron')
ON CONFLICT (name, zone) DO NOTHING;
