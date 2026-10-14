up:
    docker compose build compute airflow
    docker compose up -d --wait postgres airflow
    docker compose run --rm --no-deps compute true

airflow-up:
    docker compose build compute airflow
    docker compose up -d --wait postgres airflow

airflow-logs:
    docker compose logs -f airflow

run operation job window:
    docker compose run --rm compute python -m src.cli run {{operation}} {{job}} {{window}}

inspect layer job window:
    docker compose run --rm compute python -m src.cli inspect {{layer}} {{job}} {{window}}

report question market station day:
    docker compose run --rm compute python -m src.cli report {{question}} {{market}} {{station}} {{day}}

down:
    docker compose down --volumes --remove-orphans
