import os
from datetime import datetime, timedelta

from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import DAG, Param
from docker.types import Mount


COMPUTE_IMAGE = "meridian-compute:latest"
DOCKER_NETWORK = os.environ.get(
    "MERIDIAN_DOCKER_NETWORK",
    "meridian_meridian_network",
)
BRONZE_VOLUME = os.environ.get(
    "MERIDIAN_BRONZE_VOLUME",
    "meridian_bronze_data",
)

PUBLIC_ENVIRONMENT = {
    "BRONZE_PATH": "/data/bronze",
    "POSTGRES_DB": os.environ.get("POSTGRES_DB", "meridian"),
    "POSTGRES_USER": os.environ.get("POSTGRES_USER", "meridian"),
    "POSTGRES_HOST": "postgres",
    "POSTGRES_PORT": "5432",
}

PRIVATE_ENVIRONMENT = {
    "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", "change_me"),
}

COMMON_TASK_SETTINGS = {
    "image": COMPUTE_IMAGE,
    "docker_url": "unix://var/run/docker.sock",
    "network_mode": DOCKER_NETWORK,
    "mounts": [
        Mount(
            source=BRONZE_VOLUME,
            target="/data/bronze",
            type="volume",
        )
    ],
    "environment": PUBLIC_ENVIRONMENT,
    "private_environment": PRIVATE_ENVIRONMENT,
    "working_dir": "/app",
    "mount_tmp_dir": False,
    "auto_remove": "force",
}


with DAG(
    dag_id="meridian_bike_pipeline",
    description="Citi Bike Bronze to Silver to Gold pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={
        "owner": "meridian",
        "retries": 2,
        "retry_delay": timedelta(minutes=1),
    },
    params={
        "market": Param("jc", enum=["jc", "nyc"]),
        "month": Param(
            "2026-06",
            type="string",
            pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        ),
        "day": Param("2026-06-02", type="string", format="date"),
        "station": Param("JC115", type="string", minLength=1),
    },
    tags=["meridian", "bike-share"],
) as dag:
    ingest_to_bronze = DockerOperator(
        task_id="ingest_to_bronze",
        command=[
            "python", "-m", "src.cli", "run", "ingest-to-bronze",
            "trips:{{ params.market }}", "{{ params.month }}",
        ],
        **COMMON_TASK_SETTINGS,
    )

    transform_to_silver = DockerOperator(
        task_id="transform_to_silver",
        command=[
            "python", "-m", "src.cli", "run", "transform-to-silver",
            "trips:{{ params.market }}", "{{ params.month }}",
        ],
        **COMMON_TASK_SETTINGS,
    )

    transform_to_gold = DockerOperator(
        task_id="transform_to_gold",
        command=[
            "python", "-m", "src.cli", "run", "transform-to-gold",
            "station-daily", "{{ params.day }}",
        ],
        **COMMON_TASK_SETTINGS,
    )

    report = DockerOperator(
        task_id="report_daily_station_trips",
        command=[
            "python", "-m", "src.cli", "report", "daily-station-trips",
            "{{ params.market }}", "{{ params.station }}", "{{ params.day }}",
        ],
        **COMMON_TASK_SETTINGS,
    )

    ingest_to_bronze >> transform_to_silver >> transform_to_gold >> report
