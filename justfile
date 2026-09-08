run operation job window:
    docker compose run --rm compute python -m src.cli run {{operation}} {{job}} {{window}}

inspect layer job window:
    docker compose run --rm compute python -m src.cli inspect {{layer}} {{job}} {{window}}