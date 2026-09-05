def validate_trips_job(job: str) -> bool:
    valid_jobs = {
        "trips:jc",
        "trips:nyc",
    }

    return job in valid_jobs