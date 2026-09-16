import argparse
import json

from src.bronze_inspection import inspect_bronze
from src.bronze_sync import sync_bronze
from src.gold_transform import report_daily_station_trips, transform_to_gold
from src.job_validation import validate_trips_job
from src.silver_transform import inspect_silver, transform_to_silver
from src.window_validation import validate_day_window, validate_month_window


def _trips_coordinate(job: str, window: str) -> str:
    if not validate_trips_job(job):
        raise ValueError(f"Invalid trips job: {job}")
    if not validate_month_window(window):
        raise ValueError(f"Invalid monthly window: {window}")
    return job.split(":")[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    parser.add_argument("values", nargs="+")
    args = parser.parse_args()

    if args.command == "report":
        if len(args.values) != 4:
            raise ValueError("Report requires question, market, station and day")

        question, market, station, day = args.values
        if question != "daily-station-trips":
            raise ValueError(f"Unsupported report: {question}")
        if market not in {"jc", "nyc"}:
            raise ValueError(f"Invalid market: {market}")
        if not validate_day_window(day):
            raise ValueError(f"Invalid daily window: {day}")

        print(json.dumps(report_daily_station_trips(market, station, day)))
        return

    if args.command not in {"run", "inspect"}:
        raise ValueError(f"Unsupported command: {args.command}")
    if len(args.values) != 3:
        raise ValueError(f"{args.command} requires layer, job and window")

    action_or_layer, job, window = args.values

    if args.command == "run" and action_or_layer == "transform-to-gold":
        if job != "station-daily":
            raise ValueError(f"Invalid Gold job: {job}")
        if not validate_day_window(window):
            raise ValueError(f"Invalid daily window: {window}")

        print(json.dumps(transform_to_gold(job, window)))
        return

    market = _trips_coordinate(job, window)

    if args.command == "run":
        if action_or_layer == "ingest-to-bronze":
            sync_result = sync_bronze(market=market, window=window)
            result = {
                "sync": sync_result,
                "bronze": inspect_bronze(job, market, window),
            }
        elif action_or_layer == "transform-to-silver":
            result = transform_to_silver(job, market, window)
        else:
            raise ValueError(f"Unsupported run operation: {action_or_layer}")

        print(json.dumps(result))
        return

    if action_or_layer == "bronze":
        result = inspect_bronze(job, market, window)
    elif action_or_layer == "silver":
        result = inspect_silver(job, market, window)
    else:
        raise ValueError(f"Unsupported inspect layer: {action_or_layer}")

    print(json.dumps(result))


if __name__ == "__main__":
    main()
