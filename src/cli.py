import argparse
import json

from src.bronze_inspection import inspect_bronze
from src.job_validation import validate_trips_job
from src.window_validation import validate_month_window
from src.bronze_sync import sync_bronze
from src.silver_transform import inspect_silver, transform_to_silver


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("command")
    parser.add_argument("action_or_layer")
    parser.add_argument("job")
    parser.add_argument("window")

    args = parser.parse_args()

    # Validate job
    if not validate_trips_job(args.job):
        raise ValueError(
            f"Invalid job: {args.job}"
        )

    # Bronze / Silver currently use monthly windows
    if not validate_month_window(args.window):
        raise ValueError(
            f"Invalid monthly window: {args.window}"
        )

    # trips:jc -> jc
    # trips:nyc -> nyc
    market = args.job.split(":")[1]

    # -------------------------
    # JUST RUN
    # -------------------------
    if args.command == "run":

        if args.action_or_layer == "ingest-to-bronze":

            sync_result = sync_bronze(
                market=market,
                window=args.window,
            )

            inspection = inspect_bronze(
                job=args.job,
                market=market,
                window=args.window,
            )

            result = {
                "sync": sync_result,
                "bronze": inspection,
            }

            print(json.dumps(result))
            return

        if args.action_or_layer == "transform-to-silver":
            result = transform_to_silver(
                job=args.job,
                market=market,
                window=args.window,
            )
            print(json.dumps(result))
            return

        raise ValueError(
            f"Unsupported run operation: {args.action_or_layer}"
        )

    # -------------------------
    # JUST INSPECT
    # -------------------------
    if args.command == "inspect":

        if args.action_or_layer == "bronze":
            result = inspect_bronze(
                job=args.job,
                market=market,
                window=args.window,
            )
        elif args.action_or_layer == "silver":
            result = inspect_silver(
                job=args.job,
                market=market,
                window=args.window,
            )
        else:
            raise ValueError(
                f"Unsupported inspect layer: {args.action_or_layer}"
            )

        print(json.dumps(result))
        return

    raise ValueError(
        f"Unsupported command: {args.command}"
    )


if __name__ == "__main__":
    main()
