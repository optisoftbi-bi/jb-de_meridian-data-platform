CREATE SCHEMA IF NOT EXISTS silver;

CREATE TABLE IF NOT EXISTS silver.trips (
    ride_sk TEXT PRIMARY KEY,
    source_ride_id TEXT,
    market TEXT NOT NULL,
    source_window TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP NOT NULL,
    start_station_id TEXT NOT NULL,
    end_station_id TEXT NOT NULL,
    start_station_name TEXT,
    end_station_name TEXT,
    start_lat DOUBLE PRECISION,
    start_lng DOUBLE PRECISION,
    end_lat DOUBLE PRECISION,
    end_lng DOUBLE PRECISION,
    rideable_type TEXT,
    member_casual TEXT,
    trip_duration_seconds DOUBLE PRECISION,
    bike_id TEXT,
    birth_year INTEGER,
    gender TEXT,
    source_file TEXT NOT NULL,
    source_member TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS silver.quarantine (
    reject_id BIGSERIAL PRIMARY KEY,
    market TEXT NOT NULL,
    source_window TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_member TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    raw_record JSONB NOT NULL,
    rejection_reasons TEXT[] NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS trips_market_window_idx
    ON silver.trips (market, source_window);

CREATE INDEX IF NOT EXISTS quarantine_market_window_idx
    ON silver.quarantine (market, source_window);
