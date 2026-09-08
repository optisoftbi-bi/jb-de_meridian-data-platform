import argparse
import json

from src.bronze_ingestion import ingest_to_bronze
from src.bronze_inspection import inspect_bronze
from src.job_validation import validate_trips_job
from src.window_validation import validate_month_window


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("command")
    parser.add_argument("action_or_layer")
    parser.add_argument("job")
    parser.add_argument("window")

    args = parser.parse_args()

    if not validate_trips_job(args.job):
        raise ValueError(f"Invalid job: {args.job}")

    if not validate_month_window(args.window):
        raise ValueError(f"Invalid monthly window: {args.window}")

    market = args.job.split(":")[1]

    if args.command == "run":
        if args.action_or_layer != "ingest-to-bronze":
            raise ValueError(
                f"Unsupported run operation: {args.action_or_layer}"
            )

        destination = ingest_to_bronze(
            market=market,
            window=args.window,
        )

        print(destination)
        return

    if args.command == "inspect":
        if args.action_or_layer != "bronze":
            raise ValueError(
                f"Unsupported inspect layer: {args.action_or_layer}"
            )

        result = inspect_bronze(
            market=market,
            window=args.window,
        )

        print(json.dumps(result))
        return

    raise ValueError(
        f"Unsupported command: {args.command}"
    )


if __name__ == "__main__":
    main()