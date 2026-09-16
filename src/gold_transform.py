import os
from datetime import date, timedelta

import psycopg


def _connect():
    return psycopg.connect(
        dbname=os.environ.get("POSTGRES_DB", "meridian"),
        user=os.environ.get("POSTGRES_USER", "meridian"),
        password=os.environ.get("POSTGRES_PASSWORD", "change_me"),
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
    )


def transform_to_gold(job: str, window: str) -> dict:
    event_day = date.fromisoformat(window)
    next_day = event_day + timedelta(days=1)

    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM gold.trip_events WHERE event_day = %s",
                (event_day,),
            )

            cursor.execute(
                """
                INSERT INTO gold.dim_date (
                    day, year, month, day_of_month, day_of_week
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (day) DO NOTHING
                """,
                (
                    event_day,
                    event_day.year,
                    event_day.month,
                    event_day.day,
                    event_day.isoweekday(),
                ),
            )

            cursor.execute(
                """
                INSERT INTO gold.dim_station (
                    market, station_id, station_name, latitude, longitude
                )
                SELECT DISTINCT ON (market, station_id)
                    market, station_id, station_name, latitude, longitude
                FROM (
                    SELECT
                        market,
                        start_station_id AS station_id,
                        start_station_name AS station_name,
                        start_lat AS latitude,
                        start_lng AS longitude,
                        started_at AS event_at,
                        ride_sk
                    FROM silver.trips
                    WHERE started_at >= %s AND started_at < %s

                    UNION ALL

                    SELECT
                        market,
                        end_station_id,
                        end_station_name,
                        end_lat,
                        end_lng,
                        ended_at,
                        ride_sk
                    FROM silver.trips
                    WHERE ended_at >= %s AND ended_at < %s
                ) AS stations
                ORDER BY
                    market,
                    station_id,
                    (station_name IS NOT NULL) DESC,
                    event_at DESC,
                    ride_sk
                ON CONFLICT (market, station_id) DO UPDATE SET
                    station_name = COALESCE(
                        EXCLUDED.station_name,
                        gold.dim_station.station_name
                    ),
                    latitude = COALESCE(
                        EXCLUDED.latitude,
                        gold.dim_station.latitude
                    ),
                    longitude = COALESCE(
                        EXCLUDED.longitude,
                        gold.dim_station.longitude
                    ),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (event_day, next_day, event_day, next_day),
            )

            cursor.execute(
                """
                INSERT INTO gold.trip_events (
                    event_sk, ride_sk, market, station_id,
                    event_day, event_at, event_type
                )
                SELECT
                    ride_sk || ':departure',
                    ride_sk,
                    market,
                    start_station_id,
                    started_at::date,
                    started_at,
                    'departure'
                FROM silver.trips
                WHERE started_at >= %s AND started_at < %s

                UNION ALL

                SELECT
                    ride_sk || ':arrival',
                    ride_sk,
                    market,
                    end_station_id,
                    ended_at::date,
                    ended_at,
                    'arrival'
                FROM silver.trips
                WHERE ended_at >= %s AND ended_at < %s

                ON CONFLICT (event_sk) DO NOTHING
                """,
                (event_day, next_day, event_day, next_day),
            )

            cursor.execute(
                "SELECT COUNT(*) FROM gold.trip_events WHERE event_day = %s",
                (event_day,),
            )
            events = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM silver.trips
                     WHERE started_at >= %s AND started_at < %s)
                    +
                    (SELECT COUNT(*) FROM silver.trips
                     WHERE ended_at >= %s AND ended_at < %s)
                """,
                (event_day, next_day, event_day, next_day),
            )
            if cursor.fetchone()[0] != events:
                raise RuntimeError("Gold event reconciliation failed")

    return {
        "layer": "gold",
        "job": job,
        "window": window,
        "events": events,
    }


def report_daily_station_trips(market: str, station: str, day: str) -> dict:
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE event_type = 'departure'),
                    COUNT(*) FILTER (WHERE event_type = 'arrival')
                FROM gold.trip_events
                WHERE market = %s AND station_id = %s AND event_day = %s
                """,
                (market, station, date.fromisoformat(day)),
            )
            departures, arrivals = cursor.fetchone()

    return {
        "market": market,
        "station": station,
        "day": day,
        "departures": departures,
        "arrivals": arrivals,
    }
