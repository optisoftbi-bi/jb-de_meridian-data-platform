CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS gold.dim_date (
    day DATE PRIMARY KEY,
    year SMALLINT NOT NULL,
    month SMALLINT NOT NULL,
    day_of_month SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS gold.dim_station (
    market TEXT NOT NULL,
    station_id TEXT NOT NULL,
    station_name TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (market, station_id)
);

CREATE TABLE IF NOT EXISTS gold.trip_events (
    event_sk TEXT PRIMARY KEY,
    ride_sk TEXT NOT NULL,
    market TEXT NOT NULL,
    station_id TEXT NOT NULL,
    event_day DATE NOT NULL REFERENCES gold.dim_date(day),
    event_at TIMESTAMP NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('departure', 'arrival')),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (market, station_id)
        REFERENCES gold.dim_station(market, station_id)
);

CREATE INDEX IF NOT EXISTS trip_events_day_idx
    ON gold.trip_events (event_day);

CREATE INDEX IF NOT EXISTS trip_events_report_idx
    ON gold.trip_events (market, station_id, event_day, event_type);
