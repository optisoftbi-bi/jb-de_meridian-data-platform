from requests import request

S3_LISTING_URL = "https://s3.amazonaws.com/tripdata"


def fetch_s3_listing() -> str:
    response = request("GET", S3_LISTING_URL)
    response.raise_for_status()
    return response.text