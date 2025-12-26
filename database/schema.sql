-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Profiles Table (One-to-One with Users)
CREATE TABLE IF NOT EXISTS profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    display_name VARCHAR(50),
    icon_id VARCHAR(50) DEFAULT 'default',
    border_style VARCHAR(50) DEFAULT 'default',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sessions Table
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_code VARCHAR(10) UNIQUE NOT NULL,
    host_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'waiting', -- waiting, active, finished
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    max_players INTEGER DEFAULT 50,
    is_public BOOLEAN DEFAULT TRUE
);

-- Session Players (Join Table)
CREATE TABLE IF NOT EXISTS session_players (
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score INTEGER DEFAULT 0,
    is_eliminated BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (session_id, user_id)
);

-- Match Results (Leaderboard History)
CREATE TABLE IF NOT EXISTS match_results (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id),
    user_id INTEGER REFERENCES users(id),
    rank_position INTEGER, -- 1, 2, 3, etc.
    final_score INTEGER,
    game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
