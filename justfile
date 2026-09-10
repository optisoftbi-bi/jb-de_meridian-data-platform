up:
    docker compose build compute
    docker compose up -d postgres
    docker compose run --rm --no-deps compute true

run operation job window:
    docker compose run --rm compute python -m src.cli run {{operation}} {{job}} {{window}}

inspect layer job window:
    docker compose run --rm compute python -m src.cli inspect {{layer}} {{job}} {{window}}


down:
    docker compose down --volumes --remove-orphans
