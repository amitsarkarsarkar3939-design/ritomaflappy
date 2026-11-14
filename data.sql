PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    coin_balance INTEGER NOT NULL DEFAULT 0 CHECK (coin_balance >= 0)
);

INSERT OR IGNORE INTO profile (id, coin_balance) VALUES (1, 0);

CREATE TABLE IF NOT EXISTS game_modes (
    mode_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL,
    gravity REAL NOT NULL,
    flap_strength REAL NOT NULL,
    pipe_gap INTEGER NOT NULL,
    pipe_speed REAL NOT NULL,
    spawn_interval REAL NOT NULL
);

INSERT INTO game_modes
    (mode_id, display_name, description, gravity, flap_strength, pipe_gap, pipe_speed, spawn_interval)
VALUES
    ('classic', 'Classic', 'The balanced original challenge.', 1450, -440, 178, 190, 1.65),
    ('chill', 'Chill', 'Slower pipes and wider gaps.', 1150, -405, 220, 150, 1.90),
    ('speedy', 'Speedy', 'Fast pipes and tighter gaps.', 1550, -455, 150, 250, 1.50),
    ('horror', 'Horror', 'Spooky shadows, eerie colors, and a narrow escape.', 1500, -445, 160, 225, 1.55),
    ('fun', 'Fun', 'Bouncy flying, bright colors, and extra coins.', 1050, -390, 205, 175, 1.80),
    ('extreme', 'Extreme', 'Very fast pipes and the tightest gaps.', 1650, -470, 132, 285, 1.40)
ON CONFLICT (mode_id) DO UPDATE SET
    display_name = excluded.display_name,
    description = excluded.description,
    gravity = excluded.gravity,
    flap_strength = excluded.flap_strength,
    pipe_gap = excluded.pipe_gap,
    pipe_speed = excluded.pipe_speed,
    spawn_interval = excluded.spawn_interval;

CREATE TABLE IF NOT EXISTS best_scores (
    mode_id TEXT PRIMARY KEY REFERENCES game_modes(mode_id),
    score INTEGER NOT NULL DEFAULT 0 CHECK (score >= 0)
);

INSERT OR IGNORE INTO best_scores (mode_id, score)
SELECT mode_id, 0 FROM game_modes;

CREATE TABLE IF NOT EXISTS store_packs (
    pack_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    coins INTEGER NOT NULL CHECK (coins > 0),
    price_paise INTEGER NOT NULL CHECK (price_paise > 0),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1))
);

INSERT INTO store_packs (pack_id, display_name, coins, price_paise) VALUES
    ('mini', 'Pocket pouch', 10, 200),
    ('starter', 'Starter pouch', 100, 1000),
    ('double', 'Double pouch', 200, 2000),
    ('happy', 'Happy pouch', 350, 2500),
    ('mega', 'Mega pouch', 1000, 10000),
    ('super', 'Super pouch', 2000, 9000)
ON CONFLICT (pack_id) DO UPDATE SET
    display_name = excluded.display_name,
    coins = excluded.coins,
    price_paise = excluded.price_paise;

CREATE TABLE IF NOT EXISTS purchases (
    merchant_order_id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL REFERENCES store_packs(pack_id),
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    coins INTEGER NOT NULL CHECK (coins > 0),
    state TEXT NOT NULL CHECK (state IN ('PENDING', 'COMPLETED', 'FAILED')),
    provider_order_id TEXT,
    provider_transaction_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS purchases_state_created
    ON purchases (state, created_at);

CREATE TABLE IF NOT EXISTS wallet_ledger (
    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type TEXT NOT NULL CHECK (entry_type IN ('PLAY', 'PURCHASE')),
    coin_delta INTEGER NOT NULL,
    reference_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_accounts (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_salt BLOB NOT NULL,
    password_hash BLOB NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user_accounts(user_id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS user_sessions_expiry ON user_sessions (expires_at);

CREATE TABLE IF NOT EXISTS user_saves (
    user_id INTEGER PRIMARY KEY REFERENCES user_accounts(user_id) ON DELETE CASCADE,
    state_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);